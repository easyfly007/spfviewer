"""
Point-to-Point Resistance Solver
使用稀疏矩阵计算电阻网络中任意两个节点之间的等效电阻
"""

import numpy as np
from scipy import sparse
from scipy.sparse import linalg
from collections import defaultdict
from typing import Optional, Dict, Tuple, List, Set


class ResistanceNetwork:
    """
    电阻网络数据结构
    存储网络的所有节点和连接信息
    """
    def __init__(self):
        self.nodes: Set[str] = set()
        self.node_to_index: Dict[str, int] = {}
        self.index_to_node: Dict[int, str] = {}
        self.adjacency: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.resistance_list: List[Tuple[str, str, float]] = []
    
    def __repr__(self):
        return f"ResistanceNetwork(nodes={len(self.nodes)}, resistors={len(self.resistance_list)})"


def extract_resistance_list(net) -> List[Tuple[str, str, float]]:
    """
    从Net对象提取电阻列表
    
    Args:
        net: Net对象（来自SPFParser）
    
    Returns:
        电阻列表 [(node1_id, node2_id, resistance_value), ...]
    """
    resistance_list = []
    for element in net.get_elements():
        if element.type == 'R':  # 只处理电阻
            node1 = element.node1
            node2 = element.node2
            try:
                resistance_value = float(element.value)
                if resistance_value <= 0:
                    print(f"[WARNING] 跳过无效电阻值: {element.id} ({node1}-{node2}) = {resistance_value}")
                    continue
                resistance_list.append((node1, node2, resistance_value))
            except (ValueError, TypeError) as e:
                print(f"[WARNING] 无法解析电阻值: {element.id} = {element.value}, 错误: {e}")
                continue
    return resistance_list


def build_resistance_network(net) -> ResistanceNetwork:
    """
    从Net对象构建电阻网络
    
    Args:
        net: Net对象（来自SPFParser）
    
    Returns:
        ResistanceNetwork对象
    
    Raises:
        ValueError: 如果网络中没有有效的电阻
    """
    network = ResistanceNetwork()
    
    # 提取电阻列表
    resistance_list = extract_resistance_list(net)
    
    if not resistance_list:
        raise ValueError("网络中没有找到有效的电阻元素")
    
    network.resistance_list = resistance_list
    
    # 收集所有节点
    for node1, node2, _ in resistance_list:
        network.nodes.add(node1)
        network.nodes.add(node2)
    
    if not network.nodes:
        raise ValueError("网络中没有找到节点")
    
    # 创建节点到索引的映射
    sorted_nodes = sorted(network.nodes)
    network.node_to_index = {node: idx for idx, node in enumerate(sorted_nodes)}
    network.index_to_node = {idx: node for node, idx in network.node_to_index.items()}
    
    # 构建邻接表
    for node1, node2, resistance in resistance_list:
        network.adjacency[node1][node2] = resistance
        network.adjacency[node2][node1] = resistance
    
    return network


def validate_network(network: ResistanceNetwork) -> bool:
    """
    验证网络是否连通（使用DFS）
    
    Args:
        network: ResistanceNetwork对象
    
    Returns:
        True if 网络连通, False otherwise
    """
    if not network.nodes:
        return False
    
    if len(network.nodes) == 1:
        return True
    
    # 使用 BFS检查连通性
    visited = set()
    start_node = next(iter(network.nodes))
    queue = [start_node]
    visited.add(start_node)
    
    while queue:
        current = queue.pop(0)
        for neighbor in network.adjacency.get(current, {}).keys():
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    
    return len(visited) == len(network.nodes)


def find_reference_node(network: ResistanceNetwork, preferred: str = None) -> str:
    """
    查找合适的参考节点
    
    Args:
        network: ResistanceNetwork对象
        preferred: 首选参考节点（如果存在且有效）
    
    Returns:
        参考节点ID
    """
    if preferred and preferred in network.nodes:
        return preferred
    
    # 如果没有指定，选择连接度最大的节点（通常更稳定）
    if network.nodes:
        max_degree = -1
        best_node = None
        for node in network.nodes:
            degree = len(network.adjacency.get(node, {}))
            if degree > max_degree:
                max_degree = degree
                best_node = node
        if best_node:
            return best_node
    
    # 最后选择第一个节点
    return sorted(network.nodes)[0] if network.nodes else None


def build_sparse_conductance_matrix(network: ResistanceNetwork, 
                                     reference_node: str = None) -> Tuple[sparse.csr_matrix, Dict[str, int]]:
    """
    构建稀疏导纳矩阵（G矩阵）
    
    Args:
        network: ResistanceNetwork对象
        reference_node: 参考节点ID（如果为None，自动选择）
    
    Returns:
        (G_reduced_sparse, reduced_node_map): 
        - G_reduced_sparse: 去除参考节点后的稀疏导纳矩阵 (n-1) x (n-1), CSR格式
        - reduced_node_map: 新的节点索引映射 {node_id: reduced_index}
    
    Raises:
        ValueError: 如果参考节点不在网络中
    """
    if not network.nodes:
        raise ValueError("网络中没有节点")
    
    # 确定参考节点
    if reference_node is None:
        reference_node = find_reference_node(network)
    
    if reference_node not in network.nodes:
        raise ValueError(f"参考节点 {reference_node} 不在网络中")
    
    # 创建去除参考节点后的节点映射
    reduced_nodes = [node for node in sorted(network.nodes) if node != reference_node]
    reduced_node_map = {node: idx for idx, node in enumerate(reduced_nodes)}
    
    n_reduced = len(reduced_nodes)
    
    if n_reduced == 0:
        # 只有一个节点的情况
        return sparse.csr_matrix((0, 0)), {}
    
    # 使用COO格式构建矩阵（坐标格式，适合增量构建）
    row_indices = []
    col_indices = []
    data = []
    
    # 构建导纳矩阵
    # G[i][i] = 所有连接到节点i的导纳之和
    # G[i][j] = -1/R (如果节点i和j之间有电阻R)
    
    for node1, node2, resistance in network.resistance_list:
        # 跳过包含参考节点的电阻
        if node1 == reference_node or node2 == reference_node:
            continue
        
        conductance = 1.0 / resistance  # 导纳 = 1/电阻
        
        i = reduced_node_map[node1]
        j = reduced_node_map[node2]
        
        # 非对角元素：负导纳
        row_indices.append(i)
        col_indices.append(j)
        data.append(-conductance)
        
        row_indices.append(j)
        col_indices.append(i)
        data.append(-conductance)
        
        # 对角元素：累加导纳
        row_indices.append(i)
        col_indices.append(i)
        data.append(conductance)
        
        row_indices.append(j)
        col_indices.append(j)
        data.append(conductance)
    
    # 创建COO格式稀疏矩阵
    G_coo = sparse.coo_matrix((data, (row_indices, col_indices)), shape=(n_reduced, n_reduced))
    
    # 转换为CSR格式（适合矩阵运算）
    G_csr = G_coo.tocsr()
    
    # 消除重复项（如果有多个电阻连接同一对节点）
    G_csr.sum_duplicates()
    
    return G_csr, reduced_node_map


def calculate_equivalent_resistance(network: ResistanceNetwork, 
                                     node_a: str, 
                                     node_b: str, 
                                     reference_node: str = None,
                                     solver_type: str = 'spsolve') -> float:
    """
    计算两个节点之间的等效电阻（使用稀疏矩阵求解）
    
    Args:
        network: ResistanceNetwork对象
        node_a: 第一个节点ID
        node_b: 第二个节点ID
        reference_node: 参考节点ID（可选）
        solver_type: 求解器类型
            - 'spsolve': 直接求解（默认，适合中小型系统）
            - 'cg': 共轭梯度法（适合大型系统）
            - 'lsqr': LSQR迭代求解（适合超大型系统）
    
    Returns:
        等效电阻值（欧姆，float）
    
    Raises:
        ValueError: 如果节点不在网络中或网络无效
    """
    if node_a not in network.nodes or node_b not in network.nodes:
        raise ValueError(f"节点 {node_a} 或 {node_b} 不在网络中")
    
    if node_a == node_b:
        return 0.0
    
    # 验证网络连通性
    if not validate_network(network):
        raise ValueError("网络不连通，无法计算等效电阻")
    
    # 确定参考节点
    if reference_node is None:
        reference_node = find_reference_node(network)
    
    # 如果其中一个节点是参考节点，需要重新选择参考节点
    if node_a == reference_node or node_b == reference_node:
        # 选择另一个节点作为参考
        alternative_refs = [n for n in network.nodes if n != node_a and n != node_b]
        if alternative_refs:
            reference_node = find_reference_node(network, preferred=alternative_refs[0])
        else:
            # 只有两个节点的情况
            # 直接返回它们之间的电阻值
            if node_a in network.adjacency and node_b in network.adjacency[node_a]:
                return network.adjacency[node_a][node_b]
            else:
                raise ValueError(f"节点 {node_a} 和 {node_b} 之间没有直接连接")
    
    # 构建稀疏导纳矩阵
    G_sparse, reduced_node_map = build_sparse_conductance_matrix(network, reference_node)
    
    if G_sparse.shape[0] == 0:
        # 特殊情况：只有参考节点和另一个节点
        if node_a in network.adjacency and node_b in network.adjacency[node_a]:
            return network.adjacency[node_a][node_b]
        else:
            raise ValueError(f"无法计算节点 {node_a} 和 {node_b} 之间的等效电阻")
    
    # 检查节点是否在缩减后的网络中
    if node_a not in reduced_node_map or node_b not in reduced_node_map:
        raise ValueError(f"节点 {node_a} 或 {node_b} 不在缩减后的网络中")
    
    # 构建电流向量 I
    # 在节点A注入1A电流，在节点B流出1A电流
    n_reduced = len(reduced_node_map)
    I = np.zeros(n_reduced)
    
    idx_a = reduced_node_map[node_a]
    idx_b = reduced_node_map[node_b]
    
    I[idx_a] = 1.0   # 注入1A电流
    I[idx_b] = -1.0  # 流出1A电流
    
    # 求解线性方程组 G * V = I
    try:
        if solver_type == 'spsolve':
            # 直接求解（适合中小型系统）
            V = linalg.spsolve(G_sparse, I)
        elif solver_type == 'cg':
            # 共轭梯度法（适合大型系统）
            V, info = linalg.cg(G_sparse, I, atol=1e-10, maxiter=1000)
            if info != 0:
                print(f"[WARNING] CG求解器未收敛，info={info}")
        elif solver_type == 'lsqr':
            # LSQR迭代求解（适合超大型系统）
            V, info, itn, r1norm, r2norm = linalg.lsqr(G_sparse, I, atol=1e-10, btol=1e-10)
            if info != 0:
                print(f"[WARNING] LSQR求解器未收敛，info={info}")
        else:
            raise ValueError(f"未知的求解器类型: {solver_type}")
        
        # 等效电阻 = V[node_a] - V[node_b] (因为注入1A电流)
        voltage_a = V[idx_a]
        voltage_b = V[idx_b]
        equivalent_resistance = abs(voltage_a - voltage_b)
        
        return equivalent_resistance
        
    except Exception as e:
        raise RuntimeError(f"求解线性方程组时出错: {e}")


def solve_equivalent_resistance(net, 
                                node_a: str, 
                                node_b: str, 
                                reference_node: str = None,
                                solver_type: str = 'spsolve') -> float:
    """
    便捷函数：直接从Net对象计算等效电阻
    
    Args:
        net: Net对象
        node_a: 第一个节点ID
        node_b: 第二个节点ID
        reference_node: 参考节点ID（可选）
        solver_type: 求解器类型 ('spsolve', 'cg', 'lsqr')
    
    Returns:
        等效电阻值（欧姆）
    """
    network = build_resistance_network(net)
    return calculate_equivalent_resistance(network, node_a, node_b, reference_node, solver_type)


class SparseMatrixSolver:
    """
    稀疏矩阵求解器，支持LU分解缓存以提高批量计算性能
    """
    def __init__(self, network: ResistanceNetwork, reference_node: str = None):
        """
        初始化求解器并构建稀疏矩阵
        
        Args:
            network: ResistanceNetwork对象
            reference_node: 参考节点ID
        """
        self.network = network
        self.reference_node = reference_node if reference_node else find_reference_node(network)
        self.G_sparse, self.reduced_node_map = build_sparse_conductance_matrix(network, self.reference_node)
        self.lu_factorization = None
        self._factorized = False
    
    def factorize(self):
        """
        对矩阵进行LU分解并缓存（用于批量计算）
        """
        try:
            self.lu_factorization = linalg.splu(self.G_sparse)
            self._factorized = True
        except Exception as e:
            print(f"[WARNING] LU分解失败: {e}，将使用直接求解")
            self._factorized = False
    
    def solve(self, node_a: str, node_b: str, use_factorization: bool = True) -> float:
        """
        使用缓存的分解快速求解等效电阻
        
        Args:
            node_a: 第一个节点ID
            node_b: 第二个节点ID
            use_factorization: 是否使用LU分解（如果已分解）
        
        Returns:
            等效电阻值（欧姆）
        """
        if node_a not in self.reduced_node_map or node_b not in self.reduced_node_map:
            raise ValueError(f"节点 {node_a} 或 {node_b} 不在网络中")
        
        if node_a == node_b:
            return 0.0
        
        # 构建电流向量
        n_reduced = len(self.reduced_node_map)
        I = np.zeros(n_reduced)
        
        idx_a = self.reduced_node_map[node_a]
        idx_b = self.reduced_node_map[node_b]
        
        I[idx_a] = 1.0
        I[idx_b] = -1.0
        
        # 求解
        if use_factorization and self._factorized and self.lu_factorization is not None:
            # 使用LU分解快速求解
            V = self.lu_factorization.solve(I)
        else:
            # 直接求解
            V = linalg.spsolve(self.G_sparse, I)
        
        voltage_a = V[idx_a]
        voltage_b = V[idx_b]
        return abs(voltage_a - voltage_b)


def calculate_all_pairs_resistance(network: ResistanceNetwork, 
                                    reference_node: str = None,
                                    use_cache: bool = True) -> Dict[Tuple[str, str], float]:
    """
    计算网络中所有节点对之间的等效电阻
    
    Args:
        network: ResistanceNetwork对象
        reference_node: 参考节点ID（可选）
        use_cache: 是否使用LU分解缓存以提高性能
    
    Returns:
        {(node_a, node_b): equivalent_resistance} 字典
    """
    results = {}
    nodes_list = sorted(network.nodes)
    
    if use_cache:
        # 使用缓存的LU分解
        solver = SparseMatrixSolver(network, reference_node)
        solver.factorize()
        
        for i, node_a in enumerate(nodes_list):
            for node_b in nodes_list[i+1:]:
                try:
                    resistance = solver.solve(node_a, node_b, use_factorization=True)
                    results[(node_a, node_b)] = resistance
                except Exception as e:
                    print(f"[WARNING] 计算 {node_a}-{node_b} 时出错: {e}")
    else:
        # 逐个计算
        for i, node_a in enumerate(nodes_list):
            for node_b in nodes_list[i+1:]:
                try:
                    resistance = calculate_equivalent_resistance(network, node_a, node_b, reference_node)
                    results[(node_a, node_b)] = resistance
                except Exception as e:
                    print(f"[WARNING] 计算 {node_a}-{node_b} 时出错: {e}")
    
    return results


# 示例使用代码
if __name__ == "__main__":
    # 示例：创建简单的测试网络
    from spf_viewer.net import Net
    from spf_viewer.rcelem import RCElement
    
    # 创建测试网络
    test_net = Net("TEST", "TEST")
    
    # 添加节点（这里简化，实际应该使用Node对象）
    # 添加电阻：N1-N2=100Ω, N2-N3=200Ω, N1-N3=50Ω
    r1 = RCElement("R1", "N1", "N2", 100.0, elem_type='R')
    r2 = RCElement("R2", "N2", "N3", 200.0, elem_type='R')
    r3 = RCElement("R3", "N1", "N3", 50.0, elem_type='R')
    
    test_net.add_element(r1)
    test_net.add_element(r2)
    test_net.add_element(r3)
    
    # 计算等效电阻
    try:
        resistance = solve_equivalent_resistance(test_net, "N1", "N3")
        print(f"N1和N3之间的等效电阻: {resistance:.4f} 欧姆")
    except Exception as e:
        print(f"错误: {e}")


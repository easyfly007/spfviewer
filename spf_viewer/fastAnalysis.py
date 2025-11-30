"""
基于LRP（Least Resistance Path）树的快速RC网络分析
使用树形结构快速求解节点电压，比矩阵方法更快
"""

import heapq
from collections import defaultdict, deque
from typing import Dict, Optional, Set, Tuple, List


class LRPTreeNode:
    """LRP树节点"""
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.parent = None  # 父节点ID
        self.parent_resistor = None  # 连接到父节点的电阻ID
        self.children = []  # 子节点ID列表
        self.path_resistance = float('inf')  # 从根节点到该节点的累积电阻
        self.path_step = 0  # 从根节点到该节点经过的电阻数目，root为0
        self.current = 0.0  # 流过该节点的电流（从子节点汇总）
        self.voltage = None  # 节点电压（待计算）


def build_resistance_graph(net) -> Tuple[Dict[str, Dict[str, Tuple[str, float]]], Set[str]]:
    """
    从Net对象构建电阻图
    
    Args:
        net: Net对象
    
    Returns:
        (graph, all_nodes): 
        - graph: {node1: {node2: (resistor_id, resistance), ...}, ...}
        - all_nodes: 所有节点ID的集合
    """
    graph = defaultdict(dict)
    all_nodes = set()
    
    for element in net.get_elements():
        if element.type == 'R':  # 只考虑电阻
            try:
                resistance = float(element.value)
                if resistance <= 0:
                    continue
                
                node1 = element.node1
                node2 = element.node2
                all_nodes.add(node1)
                all_nodes.add(node2)
                
                # 双向连接
                graph[node1][node2] = (element.id, resistance)
                graph[node2][node1] = (element.id, resistance)
            except (ValueError, TypeError):
                continue
    
    return dict(graph), all_nodes


def build_lrp_tree_multi_root(graph: Dict[str, Dict[str, Tuple[str, float]]], 
                              root_nodes: Set[str],
                              all_nodes: Set[str]) -> Dict[str, LRPTreeNode]:
    """
    使用Dijkstra算法构建从多个root_node开始的最短路径树（LRP树）
    所有root节点都被视为根节点，它们的path_resistance为0，path_step为0
    
    Args:
        graph: 电阻图
        root_nodes: 根节点集合（所有P节点）
        all_nodes: 所有节点集合
    
    Returns:
        tree: {node_id: LRPTreeNode, ...}，LRP树结构
    """
    # 初始化所有树节点
    tree = {node_id: LRPTreeNode(node_id) for node_id in all_nodes}
    
    # 初始化所有根节点
    for root_node in root_nodes:
        tree[root_node].path_resistance = 0.0
        tree[root_node].path_step = 0  # root的path_step为0
    
    # Dijkstra算法：使用优先队列（按电阻距离排序）
    # 将所有根节点都加入优先队列
    pq = [(0.0, root_node) for root_node in root_nodes]
    visited = set(root_nodes)  # 所有根节点初始化为已访问
    
    while pq:
        current_path_resistance, current_node = heapq.heappop(pq)
        
        current_tree_node = tree[current_node]
        
        # 遍历邻居节点
        if current_node not in graph:
            continue
        
        for neighbor, (resistor_id, resistance) in graph[current_node].items():
            if neighbor in visited:
                continue
            
            new_path_resistance = current_path_resistance + resistance
            new_path_step = current_tree_node.path_step + 1  # 经过的电阻数目加1
            
            # 如果找到更短的路径（按电阻距离），更新
            if new_path_resistance < tree[neighbor].path_resistance:
                tree[neighbor].path_resistance = new_path_resistance
                tree[neighbor].path_step = new_path_step  # 更新经过的电阻数目
                tree[neighbor].parent = current_node
                tree[neighbor].parent_resistor = resistor_id
                
                # 更新父节点的子节点列表
                if neighbor not in tree[current_node].children:
                    tree[current_node].children.append(neighbor)
                
                heapq.heappush(pq, (new_path_resistance, neighbor))
                visited.add(neighbor)
    
    return tree


def aggregate_currents_from_leaves(tree: Dict[str, LRPTreeNode],
                                   i_node_current: Dict[str, float],
                                   graph: Dict[str, Dict[str, Tuple[str, float]]]) -> None:
    """
    从叶子节点开始，向上汇总电流到根节点
    
    Args:
        tree: LRP树结构
        i_node_current: {I节点ID: 电流值}，I节点的电流（流出为正）
        graph: 电阻图（用于查找电阻值）
    """
    # 找到所有叶子节点（没有子节点的节点）
    leaf_nodes = [node_id for node_id, node in tree.items() 
                  if not node.children]
    
    # 使用BFS从叶子节点开始，向上遍历到根节点
    # 我们需要从叶子到根的顺序，所以先找到所有节点到根的距离，然后按距离排序
    # 这里使用path_step来排序
    node_path_steps = {node_id: node.path_step for node_id, node in tree.items()}
    sorted_nodes = sorted(node_path_steps.items(), key=lambda x: x[1], reverse=True)
    
    # 初始化：I节点的电流
    for i_node, current in i_node_current.items():
        if i_node in tree:
            tree[i_node].current += current
    
    # 从最远的节点开始（按path_step），向上汇总电流
    for node_id, _ in sorted_nodes:
        node = tree[node_id]
        
        # 跳过根节点（没有父节点的节点）
        if node.parent is None:
            continue
        
        # 将当前节点的电流汇总到父节点
        parent_node = tree[node.parent]
        parent_node.current += node.current


def calculate_voltages_from_roots(tree: Dict[str, LRPTreeNode],
                                  root_nodes: Set[str],
                                  root_voltage: float,
                                  graph: Dict[str, Dict[str, Tuple[str, float]]]) -> Dict[str, float]:
    """
    从根节点开始，根据电流和电阻计算每个节点的电压
    所有根节点（P节点）的电压都是root_voltage
    
    Args:
        tree: LRP树结构
        root_nodes: 根节点集合（所有P节点）
        root_voltage: 根节点的电压值（所有P节点电压相同）
        graph: 电阻图（用于查找电阻值）
    
    Returns:
        voltages: {node_id: voltage, ...}，所有节点的电压
    """
    voltages = {}
    
    # 设置所有根节点电压
    for root_node in root_nodes:
        tree[root_node].voltage = root_voltage
        voltages[root_node] = root_voltage
    
    # 使用BFS从所有根节点开始，向下遍历树
    queue = deque(root_nodes)
    
    while queue:
        current_node_id = queue.popleft()
        current_node = tree[current_node_id]
        
        # 遍历所有子节点
        for child_id in current_node.children:
            child_node = tree[child_id]
            
            # 获取连接当前节点和子节点的电阻
            if child_node.parent_resistor is None:
                continue
            
            # 从graph中查找电阻值
            resistor_id = child_node.parent_resistor
            resistance = None
            
            # 在graph中查找电阻值
            if current_node_id in graph and child_id in graph[current_node_id]:
                _, resistance = graph[current_node_id][child_id]
            
            if resistance is None or resistance <= 0:
                # 如果找不到电阻，跳过
                continue
            
            # 计算子节点电压
            # V_child = V_parent - I * R
            # 其中I是从父节点流向子节点的电流（即子节点的current）
            current_flow = child_node.current
            child_voltage = current_node.voltage - current_flow * resistance
            
            child_node.voltage = child_voltage
            voltages[child_id] = child_voltage
            
            # 将子节点加入队列
            queue.append(child_id)
    
    # 对于不在树中的节点（未连接到P节点），电压设为None
    for node_id, node in tree.items():
        if node_id not in voltages:
            voltages[node_id] = None
    
    return voltages


def solve_rc_network_voltages_lrp(net,
                                  p_node_voltage: Dict[str, float],
                                  i_node_current: Dict[str, float]) -> Dict[str, float]:
    """
    使用LRP树方法快速求解RC网络中所有节点的电压值
    
    支持单个或多个P节点。多个P节点时，所有P节点都作为根节点构建单一LRP树。
    所有P节点的电压值必须相同。
    
    算法步骤：
    1. 从所有P节点开始，构建单一LRP（最小电阻路径）树
    2. 从叶子节点开始，向上汇总电流到根节点
    3. 从根节点开始，根据电流和电阻计算每个节点的电压
    
    Args:
        net: Net对象，包含节点和元件信息
        p_node_voltage: 字典，{*|P节点ID: 电压值}，可以包含一个或多个P节点
                       所有P节点的电压值必须相同
        i_node_current: 字典，{*|I节点ID: 电流值}，I节点的电流（流出为正）
    
    Returns:
        字典，{节点ID: 电压值}，所有节点的电压值（未连接的节点电压为None）
    
    Raises:
        ValueError: 如果网络无效或边界条件不完整
    """
    if not p_node_voltage:
        raise ValueError("必须至少有一个*|P节点")
    
    # 验证所有P节点的电压值相同
    p_voltages = list(p_node_voltage.values())
    if len(set(p_voltages)) > 1:
        raise ValueError("所有*|P节点的电压值必须相同")
    root_voltage = p_voltages[0]
    
    # 验证P节点存在
    p_nodes = set()
    for p_node_id in p_node_voltage.keys():
        p_node = net.get_node(p_node_id)
        if p_node is None:
            raise ValueError(f"*|P节点 {p_node_id} 不在网络中")
        if p_node.type != 'P':
            raise ValueError(f"节点 {p_node_id} 不是*|P类型节点")
        p_nodes.add(p_node_id)
    
    # 验证I节点存在
    for i_node_id in i_node_current.keys():
        i_node = net.get_node(i_node_id)
        if i_node is None:
            raise ValueError(f"*|I节点 {i_node_id} 不在网络中")
        if i_node.type != 'I':
            raise ValueError(f"节点 {i_node_id} 不是*|I类型节点")
    
    # 构建电阻图
    graph, all_nodes = build_resistance_graph(net)
    
    # 检查所有P节点是否连接到电阻
    for p_node_id in p_nodes:
        if p_node_id not in all_nodes:
            raise ValueError(f"*|P节点 {p_node_id} 没有连接到任何电阻")
    
    # 构建LRP树（所有P节点都作为根节点）
    tree = build_lrp_tree_multi_root(graph, p_nodes, all_nodes)
    
    # 从叶子节点开始，向上汇总电流
    aggregate_currents_from_leaves(tree, i_node_current, graph)
    
    # 从根节点开始，计算电压
    voltages = calculate_voltages_from_roots(tree, p_nodes, root_voltage, graph)
    
    return voltages

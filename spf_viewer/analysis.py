"""
RC网络分析模块
用于求解RC网络中的节点电压
"""

import numpy as np
from scipy import sparse
from scipy.sparse import linalg
from typing import Dict, Optional, Tuple
from collections import defaultdict


def solve_rc_network_voltages(net, 
                               p_node_voltage: Dict[str, float],
                               i_node_current: Dict[str, float],
                               reference_node: Optional[str] = None,
                               frequency: float = 0.0,
                               solver_type: str = 'spsolve') -> Dict[str, float]:
    """
    求解RC网络中所有节点的电压值
    
    给定条件：
    - *|P 节点：给定电压值（电压源）
    - *|I 节点：给定电流值（电流源）
    
    Args:
        net: Net对象，包含节点和元件信息
        p_node_voltage: 字典，{节点ID: 电压值}，所有*|P类型节点的电压
        i_node_current: 字典，{节点ID: 电流值}，所有*|I类型节点的电流
        reference_node: 参考节点ID（如果为None，自动选择）
        frequency: 频率（Hz），用于计算电容导纳。0表示DC分析（电容开路）
        solver_type: 求解器类型 ('spsolve', 'cg', 'lsqr')
    
    Returns:
        字典，{节点ID: 电压值}，所有节点的电压值
    
    Raises:
        ValueError: 如果网络无效或边界条件不完整
    """
    # 收集所有节点
    all_nodes = {}
    p_nodes = set()
    i_nodes = set()
    
    for node in net.get_nodes():
        all_nodes[node.id] = node
        if node.type == 'P':
            p_nodes.add(node.id)
        elif node.type == 'I':
            i_nodes.add(node.id)
    
    if not all_nodes:
        raise ValueError("网络中没有节点")
    
    # 验证边界条件
    if not p_nodes:
        raise ValueError("网络中必须至少有一个*|P节点作为电压源")
    
    for p_node in p_nodes:
        if p_node not in p_node_voltage:
            raise ValueError(f"*|P节点 {p_node} 的电压值未指定")
    
    for i_node in i_nodes:
        if i_node not in i_node_current:
            raise ValueError(f"*|I节点 {i_node} 的电流值未指定")
    
    # 确定参考节点（优先使用第一个P节点）
    if reference_node is None:
        if p_nodes:
            reference_node = next(iter(p_nodes))
        else:
            # 如果没有P节点，选择第一个节点
            reference_node = next(iter(all_nodes.keys()))
    
    if reference_node not in all_nodes:
        raise ValueError(f"参考节点 {reference_node} 不在网络中")
    
    # 提取所有元件（R和C）
    elements = []
    for element in net.get_elements():
        if element.type in ['R', 'C']:
            elements.append(element)
    
    if not elements:
        raise ValueError("网络中没有有效的R或C元件")
    
    # 构建节点到索引的映射（排除参考节点）
    reduced_nodes = [node_id for node_id in sorted(all_nodes.keys()) 
                     if node_id != reference_node]
    reduced_node_map = {node_id: idx for idx, node_id in enumerate(reduced_nodes)}
    n_reduced = len(reduced_nodes)
    
    if n_reduced == 0:
        # 只有一个节点（参考节点）的情况
        return {reference_node: p_node_voltage.get(reference_node, 0.0)}
    
    # 构建导纳矩阵
    row_indices = []
    col_indices = []
    data = []
    
    # 计算电容导纳（DC分析时，频率=0，电容开路）
    omega = 2 * np.pi * frequency if frequency > 0 else 0.0
    
    # 获取参考节点电压
    v_ref = p_node_voltage.get(reference_node, 0.0)
    
    for element in elements:
        node1 = element.node1
        node2 = element.node2
        
        # 计算导纳
        if element.type == 'R':
            try:
                resistance = float(element.value)
                if resistance <= 0:
                    continue
                conductance = 1.0 / resistance
            except (ValueError, TypeError):
                continue
        elif element.type == 'C':
            if frequency == 0:
                # DC分析，电容开路，忽略
                continue
            try:
                capacitance = float(element.value)
                if capacitance <= 0:
                    continue
                # 导纳 = j * omega * C，这里只处理实部（如果是AC分析，需要复数）
                # 为简化，这里假设是DC或低频分析，忽略电容
                conductance = omega * capacitance
            except (ValueError, TypeError):
                continue
        else:
            continue
        
        # 处理连接到参考节点的元件
        if node1 == reference_node:
            # node2 连接到参考节点
            if node2 in reduced_node_map:
                idx = reduced_node_map[node2]
                # 在对角元素上加上导纳
                row_indices.append(idx)
                col_indices.append(idx)
                data.append(conductance)
        elif node2 == reference_node:
            # node1 连接到参考节点
            if node1 in reduced_node_map:
                idx = reduced_node_map[node1]
                # 在对角元素上加上导纳
                row_indices.append(idx)
                col_indices.append(idx)
                data.append(conductance)
        else:
            # 两个节点都不是参考节点
            if node1 not in reduced_node_map or node2 not in reduced_node_map:
                continue
            
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
    
    # 创建稀疏矩阵
    if not data:
        raise ValueError("无法构建导纳矩阵，可能所有元件都连接到参考节点")
    
    G_coo = sparse.coo_matrix((data, (row_indices, col_indices)), 
                              shape=(n_reduced, n_reduced))
    G_csr = G_coo.tocsr()
    G_csr.sum_duplicates()
    
    # 构建电流向量
    I = np.zeros(n_reduced)
    
    # 处理连接到参考节点的元件对电流向量的贡献
    # 对于连接到参考节点的电阻R，如果参考节点电压为V_ref，非参考节点为V_i
    # 则从节点i流向参考节点的电流为 G * (V_i - V_ref) = G * V_i - G * V_ref
    # 在节点i的KCL方程中，-G * V_ref 项会出现在电流向量中
    for element in elements:
        node1 = element.node1
        node2 = element.node2
        
        if element.type == 'R':
            try:
                resistance = float(element.value)
                if resistance <= 0:
                    continue
                conductance = 1.0 / resistance
            except (ValueError, TypeError):
                continue
        elif element.type == 'C':
            if frequency == 0:
                continue
            try:
                capacitance = float(element.value)
                if capacitance <= 0:
                    continue
                conductance = omega * capacitance
            except (ValueError, TypeError):
                continue
        else:
            continue
        
        # 处理连接到参考节点的元件
        if node1 == reference_node and node2 in reduced_node_map:
            idx = reduced_node_map[node2]
            # 电流贡献：-G * V_ref（因为电流从node2流向参考节点）
            I[idx] -= conductance * v_ref
        elif node2 == reference_node and node1 in reduced_node_map:
            idx = reduced_node_map[node1]
            # 电流贡献：-G * V_ref（因为电流从node1流向参考节点）
            I[idx] -= conductance * v_ref
    
    # 添加*|I节点的电流源
    for i_node, current in i_node_current.items():
        if i_node in reduced_node_map:
            idx = reduced_node_map[i_node]
            I[idx] += current
        elif i_node == reference_node:
            # 如果电流源在参考节点，需要从其他节点流出
            # 这里简化处理：将电流分配到所有连接的节点
            pass
    
    # 处理*|P节点（电压源）
    # 对于P节点，我们需要修改方程组：V[P] = V_given
    # 方法：将P节点的行替换为 V[P] = V_given，并调整其他方程
    
    # 找出所有P节点（排除参考节点）
    p_nodes_reduced = [node_id for node_id in p_nodes if node_id in reduced_node_map]
    
    if p_nodes_reduced:
        # 对于每个P节点，我们知道其电压值，可以将其从方程组中移除
        # 或者修改矩阵，将P节点的行设为单位向量
        
        for p_node in p_nodes_reduced:
            p_idx = reduced_node_map[p_node]
            v_p = p_node_voltage[p_node]
            
            # 获取P节点所在行的非零元素
            row_start = G_csr.indptr[p_idx]
            row_end = G_csr.indptr[p_idx + 1]
            
            # 计算这一行对电流向量的贡献（需要减去）
            for k in range(row_start, row_end):
                col_idx = G_csr.indices[k]
                val = G_csr.data[k]
                if col_idx != p_idx:  # 非对角元素
                    I[col_idx] -= val * v_p
            
            # 将P节点的行清零，然后设置对角元素为1
            G_csr.data[row_start:row_end] = 0.0
            # 设置对角元素
            G_csr[p_idx, p_idx] = 1.0
            G_csr.sum_duplicates()
            
            # 设置电流向量
            I[p_idx] = v_p
    
    # 求解线性方程组 G * V = I
    try:
        if solver_type == 'spsolve':
            V_reduced = linalg.spsolve(G_csr, I)
        elif solver_type == 'cg':
            V_reduced, info = linalg.cg(G_csr, I, atol=1e-10, maxiter=1000)
            if info != 0:
                raise RuntimeError(f"CG求解器未收敛，info={info}")
        elif solver_type == 'lsqr':
            V_reduced, info, itn, r1norm, r2norm = linalg.lsqr(G_csr, I, atol=1e-10, btol=1e-10)
            if info != 0:
                raise RuntimeError(f"LSQR求解器未收敛，info={info}")
        else:
            raise ValueError(f"未知的求解器类型: {solver_type}")
    except Exception as e:
        raise RuntimeError(f"求解线性方程组时出错: {e}")
    
    # 构建完整的电压字典
    voltages = {}
    
    # 参考节点电压
    voltages[reference_node] = p_node_voltage.get(reference_node, 0.0)
    
    # 其他节点电压
    for node_id, idx in reduced_node_map.items():
        voltages[node_id] = float(V_reduced[idx])
    
    return voltages


def solve_rc_network_voltages_simple(net,
                                     p_node_id: str,
                                     p_voltage: float,
                                     i_node_currents: Dict[str, float],
                                     reference_node: Optional[str] = None,
                                     frequency: float = 0.0) -> Dict[str, float]:
    """
    简化版本的求解函数，只有一个*|P节点
    
    Args:
        net: Net对象
        p_node_id: *|P节点ID
        p_voltage: *|P节点的电压值
        i_node_currents: 字典，{*|I节点ID: 电流值}
        reference_node: 参考节点（可选）
        frequency: 频率（Hz），0表示DC分析
    
    Returns:
        字典，{节点ID: 电压值}
    """
    return solve_rc_network_voltages(
        net=net,
        p_node_voltage={p_node_id: p_voltage},
        i_node_current=i_node_currents,
        reference_node=reference_node,
        frequency=frequency
    )
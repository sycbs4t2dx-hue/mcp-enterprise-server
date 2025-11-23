/**
 * MCP Enterprise Server 管理UI - 类型定义
 */

// WebSocket消息类型
export interface WSMessage {
  type: string;
  channel?: string;
  data?: any;
  timestamp?: string;
}

// 连接池统计
export interface PoolStats {
  pool_size: number;
  active_connections: number;
  idle_connections: number;
  overflow_connections: number;
  utilization: number;
  qps: number;
  avg_query_time: number;
  max_wait_time: number;
  total_queries: number;
  timestamp: string;
}

// 向量检索统计
export interface VectorSearchStats {
  total_searches: number;
  avg_search_time: number;
  p95_search_time: number;
  p99_search_time: number;
  recall_rate: number;
  top_k_distribution: Record<number, number>;
  timestamp: string;
}

// 错误防火墙事件
export interface ErrorFirewallEvent {
  error_id: string;
  error_scene: string;
  error_type: string;
  solution: string;
  confidence: number;
  timestamp: string;
  status: 'blocked' | 'passed';
}

// 系统告警
export interface SystemAlert {
  alert_id: string;
  level: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  source: string;
  timestamp: string;
  resolved: boolean;
}

// 概览统计
export interface OverviewStats {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_response_time: number;
  active_connections: number;
  memory_usage: number;
  cpu_usage: number;
  uptime: number;
  timestamp: string;
}

// 活动日志
export interface ActivityLog {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  description: string;
  timestamp: string;
  channel: string;
}

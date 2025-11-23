/**
 * 统一的自定义Hooks
 * 消除前端代码重复，提供可复用的逻辑
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

/**
 * 统一的API配置
 */
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8765';

/**
 * 创建axios实例
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

/**
 * useInitialStats - 统一的初始数据加载Hook
 *
 * @param endpoint - API端点
 * @param defaultValue - 默认值
 * @param onSuccess - 成功回调
 * @param onError - 错误回调
 *
 * @example
 * const { data, loading, error, reload } = useInitialStats(
 *   '/api/v1/stats?include=system',
 *   { total_requests: 0 },
 *   (data) => console.log('数据加载成功:', data),
 *   (err) => console.error('加载失败:', err)
 * );
 */
export function useInitialStats<T = any>(
  endpoint: string,
  defaultValue: T,
  onSuccess?: (data: T) => void,
  onError?: (error: Error) => void
) {
  const [data, setData] = useState<T>(defaultValue);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(endpoint);
      const result = response.data.data || response.data;

      setData(result);
      onSuccess?.(result);

      console.log(`✅ ${endpoint} 数据加载成功:`, result);
    } catch (err) {
      const error = err as Error;
      setError(error);
      onError?.(error);

      console.error(`❌ ${endpoint} 数据加载失败:`, error);
    } finally {
      setLoading(false);
    }
  }, [endpoint, onSuccess, onError]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    reload: fetchData
  };
}

/**
 * useWebSocketStats - 统一的WebSocket统计订阅Hook
 *
 * @param channel - WebSocket频道
 * @param eventType - 事件类型
 * @param initialValue - 初始值
 * @param transformer - 数据转换函数
 *
 * @example
 * const stats = useWebSocketStats(
 *   'system_stats',
 *   'stats_update',
 *   { cpu: 0, memory: 0 },
 *   (data) => ({ ...data, timestamp: new Date() })
 * );
 */
export function useWebSocketStats<T = any>(
  channel: string,
  eventType: string | string[],
  initialValue: T,
  transformer?: (data: any) => T
) {
  const [data, setData] = useState<T>(initialValue);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      // 断开现有连接
      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(`ws://localhost:8765/ws`);

      ws.onopen = () => {
        console.log(`📡 WebSocket连接成功 (${channel})`);
        setConnected(true);

        // 订阅频道
        ws.send(JSON.stringify({
          type: 'subscribe',
          channels: [channel]
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          // 检查频道和事件类型
          if (message.channel === channel) {
            const eventTypes = Array.isArray(eventType) ? eventType : [eventType];

            if (eventTypes.includes(message.type) && message.data) {
              const transformedData = transformer ? transformer(message.data) : message.data;
              setData(transformedData);

              console.log(`📊 收到${channel}/${message.type}数据:`, transformedData);
            }
          }
        } catch (err) {
          console.error('WebSocket消息解析失败:', err);
        }
      };

      ws.onerror = (error) => {
        console.error(`❌ WebSocket错误 (${channel}):`, error);
      };

      ws.onclose = () => {
        console.log(`🔌 WebSocket断开 (${channel})`);
        setConnected(false);

        // 自动重连
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connect();
          }, 3000);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket连接失败:', error);
      setConnected(false);
    }
  }, [channel, eventType, transformer]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    data,
    connected,
    reconnect: connect
  };
}

/**
 * useLocalStorage - localStorage持久化Hook
 *
 * @param key - 存储键名
 * @param initialValue - 初始值
 * @param maxAge - 最大缓存时间（毫秒）
 *
 * @example
 * const [chartData, setChartData] = useLocalStorage(
 *   'pool_chart_data',
 *   { time: [], values: [] },
 *   3600000 // 1小时
 * );
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
  maxAge?: number
) {
  // 从localStorage读取初始值
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      if (!item) return initialValue;

      const parsed = JSON.parse(item);

      // 检查缓存是否过期
      if (maxAge && parsed.timestamp) {
        const age = Date.now() - parsed.timestamp;
        if (age > maxAge) {
          console.log(`🗑️ localStorage缓存已过期: ${key}`);
          window.localStorage.removeItem(key);
          return initialValue;
        }
      }

      console.log(`📦 从localStorage恢复数据: ${key}`);
      return parsed.data || parsed;
    } catch (error) {
      console.error(`localStorage读取失败: ${key}`, error);
      return initialValue;
    }
  });

  // 保存到localStorage
  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;

      setStoredValue(valueToStore);

      const dataToSave = maxAge
        ? { data: valueToStore, timestamp: Date.now() }
        : valueToStore;

      window.localStorage.setItem(key, JSON.stringify(dataToSave));
      console.log(`💾 保存到localStorage: ${key}`);
    } catch (error) {
      console.error(`localStorage写入失败: ${key}`, error);
    }
  };

  // 清除缓存
  const clearValue = () => {
    window.localStorage.removeItem(key);
    setStoredValue(initialValue);
    console.log(`🗑️ 清除localStorage: ${key}`);
  };

  return [storedValue, setValue, clearValue] as const;
}

/**
 * usePolling - 定期轮询Hook
 *
 * @param callback - 轮询回调函数
 * @param interval - 轮询间隔（毫秒）
 * @param enabled - 是否启用
 *
 * @example
 * usePolling(
 *   async () => {
 *     const data = await fetchStats();
 *     setStats(data);
 *   },
 *   5000, // 5秒
 *   true
 * );
 */
export function usePolling(
  callback: () => void | Promise<void>,
  interval: number = 5000,
  enabled: boolean = true
) {
  const savedCallback = useRef(callback);
  const intervalIdRef = useRef<NodeJS.Timeout | null>(null);

  // 更新回调
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // 设置轮询
  useEffect(() => {
    if (!enabled) {
      if (intervalIdRef.current) {
        clearInterval(intervalIdRef.current);
        intervalIdRef.current = null;
      }
      return;
    }

    const tick = async () => {
      try {
        await savedCallback.current();
      } catch (error) {
        console.error('轮询执行失败:', error);
      }
    };

    intervalIdRef.current = setInterval(tick, interval);

    return () => {
      if (intervalIdRef.current) {
        clearInterval(intervalIdRef.current);
      }
    };
  }, [interval, enabled]);
}

/**
 * useDebounce - 防抖Hook
 *
 * @param value - 需要防抖的值
 * @param delay - 延迟时间（毫秒）
 *
 * @example
 * const [searchTerm, setSearchTerm] = useState('');
 * const debouncedSearchTerm = useDebounce(searchTerm, 500);
 *
 * useEffect(() => {
 *   if (debouncedSearchTerm) {
 *     // 执行搜索
 *   }
 * }, [debouncedSearchTerm]);
 */
export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * useCombinedStats - 组合多个统计源的Hook
 *
 * @param sources - 数据源配置
 *
 * @example
 * const stats = useCombinedStats({
 *   initial: { endpoint: '/api/v1/stats', key: 'system' },
 *   websocket: { channel: 'system_stats', event: 'update' },
 *   localStorage: { key: 'system_stats_cache', maxAge: 60000 }
 * });
 */
export function useCombinedStats<T = any>(sources: {
  initial?: {
    endpoint: string;
    key?: string;
    defaultValue?: T;
  };
  websocket?: {
    channel: string;
    event: string | string[];
    transformer?: (data: any) => Partial<T>;
  };
  localStorage?: {
    key: string;
    maxAge?: number;
  };
}) {
  const [combinedData, setCombinedData] = useState<T>(
    sources.initial?.defaultValue || {} as T
  );

  // 初始数据加载
  const initialData = sources.initial
    ? useInitialStats(
        sources.initial.endpoint,
        sources.initial.defaultValue || {} as T,
        (data) => {
          const extractedData = sources.initial?.key
            ? data[sources.initial.key]
            : data;
          setCombinedData(prev => ({ ...prev, ...extractedData }));
        }
      )
    : null;

  // WebSocket订阅
  const wsData = sources.websocket
    ? useWebSocketStats(
        sources.websocket.channel,
        sources.websocket.event,
        {} as Partial<T>,
        sources.websocket.transformer
      )
    : null;

  // localStorage持久化
  const [cachedData, setCachedData] = sources.localStorage
    ? useLocalStorage(
        sources.localStorage.key,
        {} as T,
        sources.localStorage.maxAge
      )
    : [null, null, null];

  // 合并WebSocket数据
  useEffect(() => {
    if (wsData?.data && Object.keys(wsData.data).length > 0) {
      setCombinedData(prev => ({ ...prev, ...wsData.data }));

      // 同时更新缓存
      if (setCachedData) {
        setCachedData(prev => ({ ...prev, ...wsData.data }));
      }
    }
  }, [wsData?.data, setCachedData]);

  // 从缓存恢复
  useEffect(() => {
    if (cachedData && Object.keys(cachedData).length > 0) {
      setCombinedData(prev => ({ ...prev, ...cachedData }));
    }
  }, []); // 只在组件挂载时执行

  return {
    data: combinedData,
    loading: initialData?.loading || false,
    error: initialData?.error || null,
    connected: wsData?.connected || false,
    reload: initialData?.reload,
    clearCache: sources.localStorage ? cachedData[2] : undefined
  };
}

export default {
  useInitialStats,
  useWebSocketStats,
  useLocalStorage,
  usePolling,
  useDebounce,
  useCombinedStats
};
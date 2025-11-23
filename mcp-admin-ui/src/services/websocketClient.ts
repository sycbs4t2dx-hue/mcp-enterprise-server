/**
 * WebSocket客户端服务
 * 用于前端连接和实时通信
 */

import { EventEmitter } from 'events';

export enum MessageType {
  // 连接管理
  CONNECT = 'connect',
  DISCONNECT = 'disconnect',
  HEARTBEAT = 'heartbeat',
  SUBSCRIBE = 'subscribe',
  UNSUBSCRIBE = 'unsubscribe',

  // 协作消息
  AGENT_STATUS = 'agent_status',
  LOCK_UPDATE = 'lock_update',
  TASK_UPDATE = 'task_update',
  CONFLICT_ALERT = 'conflict_alert',

  // 学习消息
  PATTERN_DETECTED = 'pattern_detected',
  EXPERIENCE_SHARED = 'experience_shared',
  LEARNING_UPDATE = 'learning_update',

  // 系统消息
  SYSTEM_ALERT = 'system_alert',
  PROGRESS_UPDATE = 'progress_update',
  ERROR_NOTIFICATION = 'error_notification'
}

export interface WebSocketMessage {
  type: MessageType;
  payload: any;
  sender?: string;
  timestamp: string;
}

export interface WebSocketConfig {
  url?: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  debug?: boolean;
}

export class WebSocketClient extends EventEmitter {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private clientId: string | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private subscriptions: Set<string> = new Set();
  private messageQueue: WebSocketMessage[] = [];
  private isConnected: boolean = false;

  constructor(config: WebSocketConfig = {}) {
    super();
    this.config = {
      url: config.url || 'ws://localhost:8766',
      reconnect: config.reconnect !== false,
      reconnectInterval: config.reconnectInterval || 5000,
      heartbeatInterval: config.heartbeatInterval || 30000,
      debug: config.debug || false
    };
  }

  /**
   * 连接到WebSocket服务器
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.log('Connecting to WebSocket server...');
        this.ws = new WebSocket(this.config.url!);

        this.ws.onopen = () => {
          this.log('WebSocket connected');
          this.isConnected = true;
          this.emit('connected');

          // 发送排队的消息
          this.flushMessageQueue();

          // 启动心跳
          this.startHeartbeat();

          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onerror = (error) => {
          this.log('WebSocket error:', error);
          this.emit('error', error);
          reject(error);
        };

        this.ws.onclose = (event) => {
          this.log('WebSocket disconnected');
          this.isConnected = false;
          this.emit('disconnected', event);

          // 停止心跳
          this.stopHeartbeat();

          // 自动重连
          if (this.config.reconnect && !event.wasClean) {
            this.scheduleReconnect();
          }
        };
      } catch (error) {
        this.log('Connection error:', error);
        reject(error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.config.reconnect = false;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * 发送消息
   */
  send(type: MessageType, payload: any): void {
    const message: WebSocketMessage = {
      type,
      payload,
      timestamp: new Date().toISOString()
    };

    if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
      this.log('Message sent:', message);
    } else {
      // 加入队列等待连接
      this.messageQueue.push(message);
      this.log('Message queued:', message);
    }
  }

  /**
   * 订阅频道
   */
  subscribe(channel: string): void {
    this.subscriptions.add(channel);
    this.send(MessageType.SUBSCRIBE, { channel });
    this.log('Subscribed to channel:', channel);
  }

  /**
   * 取消订阅
   */
  unsubscribe(channel: string): void {
    this.subscriptions.delete(channel);
    this.send(MessageType.UNSUBSCRIBE, { channel });
    this.log('Unsubscribed from channel:', channel);
  }

  /**
   * 处理收到的消息
   */
  private handleMessage(data: string): void {
    try {
      const message: WebSocketMessage = JSON.parse(data);
      this.log('Message received:', message);

      // 处理特殊消息类型
      switch (message.type) {
        case MessageType.CONNECT:
          this.clientId = message.payload.client_id;
          this.emit('client_id', this.clientId);
          break;

        case MessageType.HEARTBEAT:
          // 心跳响应
          break;

        case MessageType.AGENT_STATUS:
          this.emit('agent_status', message.payload);
          break;

        case MessageType.LOCK_UPDATE:
          this.emit('lock_update', message.payload);
          break;

        case MessageType.TASK_UPDATE:
          this.emit('task_update', message.payload);
          break;

        case MessageType.CONFLICT_ALERT:
          this.emit('conflict_alert', message.payload);
          break;

        case MessageType.PATTERN_DETECTED:
          this.emit('pattern_detected', message.payload);
          break;

        case MessageType.EXPERIENCE_SHARED:
          this.emit('experience_shared', message.payload);
          break;

        case MessageType.LEARNING_UPDATE:
          this.emit('learning_update', message.payload);
          break;

        case MessageType.SYSTEM_ALERT:
          this.emit('system_alert', message.payload);
          break;

        case MessageType.PROGRESS_UPDATE:
          this.emit('progress_update', message.payload);
          break;

        case MessageType.ERROR_NOTIFICATION:
          this.emit('error_notification', message.payload);
          break;
      }

      // 发射通用消息事件
      this.emit('message', message);

    } catch (error) {
      this.log('Error parsing message:', error);
    }
  }

  /**
   * 开始心跳
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send(MessageType.HEARTBEAT, {});
      }
    }, this.config.heartbeatInterval!);
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * 调度重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;

    this.log(`Reconnecting in ${this.config.reconnectInterval}ms...`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch((error) => {
        this.log('Reconnection failed:', error);
        this.scheduleReconnect();
      });
    }, this.config.reconnectInterval!);
  }

  /**
   * 发送队列中的消息
   */
  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()!;
      this.send(message.type, message.payload);
    }
  }

  /**
   * 日志输出
   */
  private log(...args: any[]): void {
    if (this.config.debug) {
      console.log('[WebSocket]', ...args);
    }
  }

  /**
   * 获取连接状态
   */
  getState(): {
    connected: boolean;
    clientId: string | null;
    subscriptions: string[];
  } {
    return {
      connected: this.isConnected,
      clientId: this.clientId,
      subscriptions: Array.from(this.subscriptions)
    };
  }
}

// ============================================
// React Hook
// ============================================

import { useEffect, useState, useCallback, useRef } from 'react';

export interface UseWebSocketOptions {
  url?: string;
  reconnect?: boolean;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: any) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const [connected, setConnected] = useState(false);
  const [clientId, setClientId] = useState<string | null>(null);
  const clientRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    const client = new WebSocketClient({
      url: options.url,
      reconnect: options.reconnect,
      debug: process.env.NODE_ENV === 'development'
    });

    clientRef.current = client;

    // 设置事件监听
    client.on('connected', () => {
      setConnected(true);
      options.onConnect?.();
    });

    client.on('disconnected', () => {
      setConnected(false);
      options.onDisconnect?.();
    });

    client.on('client_id', (id: string) => {
      setClientId(id);
    });

    client.on('message', (message: WebSocketMessage) => {
      options.onMessage?.(message);
    });

    client.on('error', (error: any) => {
      options.onError?.(error);
    });

    // 连接
    client.connect().catch(console.error);

    // 清理
    return () => {
      client.disconnect();
    };
  }, []);

  const send = useCallback((type: MessageType, payload: any) => {
    clientRef.current?.send(type, payload);
  }, []);

  const subscribe = useCallback((channel: string) => {
    clientRef.current?.subscribe(channel);
  }, []);

  const unsubscribe = useCallback((channel: string) => {
    clientRef.current?.unsubscribe(channel);
  }, []);

  return {
    connected,
    clientId,
    send,
    subscribe,
    unsubscribe
  };
}

// ============================================
// 单例实例
// ============================================

let globalClient: WebSocketClient | null = null;

export function getWebSocketClient(): WebSocketClient {
  if (!globalClient) {
    globalClient = new WebSocketClient();
  }
  return globalClient;
}

export default WebSocketClient;
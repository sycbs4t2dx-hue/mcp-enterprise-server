/**
 * WebSocket客户端服务
 * 连接MCP Enterprise Server的WebSocket端点
 */

import type { WSMessage } from '../types';

export type MessageHandler = (message: WSMessage) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 999; // 几乎无限重连
  private reconnectDelay = 3000;
  private messageHandlers: Set<MessageHandler> = new Set();
  private subscribedChannels: Set<string> = new Set();
  private isConnecting = false;
  private manualDisconnect = false; // 标记是否手动断开
  private heartbeatInterval: number | null = null;
  private heartbeatDelay = 30000; // 30秒心跳

  constructor(url: string = 'ws://localhost:8765/ws', clientId: string = 'admin-ui') {
    this.url = url;
    this.clientId = clientId;

    // 监听页面可见性变化
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        // 页面重新可见时，检查连接
        if (!this.connected && !this.manualDisconnect) {
          console.log('🔄 页面重新可见，检查连接...');
          this.reconnectAttempts = 0; // 重置重连计数
          this.connect().catch(err => console.error('自动连接失败:', err));
        }
      }
    });

    // 监听在线状态
    window.addEventListener('online', () => {
      console.log('🌐 网络恢复，尝试重连...');
      this.reconnectAttempts = 0;
      this.connect().catch(err => console.error('网络恢复重连失败:', err));
    });
  }

  /**
   * 连接WebSocket
   */
  connect(): Promise<void> {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      console.log('WebSocket已连接或正在连接');
      return Promise.resolve();
    }

    this.isConnecting = true;
    this.manualDisconnect = false; // 重置手动断开标志

    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${this.url}?client_id=${this.clientId}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('✅ WebSocket连接成功');
          this.isConnecting = false;
          this.reconnectAttempts = 0;

          // 重新订阅所有频道
          this.subscribedChannels.forEach(channel => {
            this.subscribe(channel);
          });

          // 启动心跳
          this.startHeartbeat();

          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WSMessage = JSON.parse(event.data);
            console.log('📨 收到消息:', message);

            // 通知所有订阅者
            this.messageHandlers.forEach(handler => {
              try {
                handler(message);
              } catch (err) {
                console.error('消息处理错误:', err);
              }
            });
          } catch (err) {
            console.error('消息解析错误:', err);
          }
        };

        this.ws.onerror = (error) => {
          console.error('❌ WebSocket错误:', error);
          this.isConnecting = false;
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('👋 WebSocket连接关闭');
          this.isConnecting = false;
          this.ws = null;
          this.stopHeartbeat();

          // 只在非手动断开时自动重连
          if (!this.manualDisconnect) {
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
              this.reconnectAttempts++;
              const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 30000);
              console.log(`🔄 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts}) - ${delay}ms后...`);
              setTimeout(() => {
                this.connect().catch(err => {
                  console.error('重连失败:', err);
                });
              }, delay);
            } else {
              console.error('❌ 达到最大重连次数，停止重连');
            }
          }
        };
      } catch (err) {
        this.isConnecting = false;
        reject(err);
      }
    });
  }

  /**
   * 启动心跳
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = window.setInterval(() => {
      this.ping();
    }, this.heartbeatDelay);
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval !== null) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * 订阅频道
   */
  subscribe(channel: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接，暂存订阅请求:', channel);
      this.subscribedChannels.add(channel);
      return;
    }

    this.ws.send(JSON.stringify({
      action: 'subscribe',
      channel: channel
    }));

    this.subscribedChannels.add(channel);
    console.log(`✅ 订阅频道: ${channel}`);
  }

  /**
   * 取消订阅频道
   */
  unsubscribe(channel: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接');
      return;
    }

    this.ws.send(JSON.stringify({
      action: 'unsubscribe',
      channel: channel
    }));

    this.subscribedChannels.delete(channel);
    console.log(`❌ 取消订阅: ${channel}`);
  }

  /**
   * 注册消息处理器
   */
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);

    // 返回取消订阅函数
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  /**
   * 发送ping
   */
  ping(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接');
      return;
    }

    this.ws.send(JSON.stringify({
      action: 'ping'
    }));
  }

  /**
   * 获取统计信息
   */
  getStats(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接');
      return;
    }

    this.ws.send(JSON.stringify({
      action: 'get_stats'
    }));
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.ws) {
      this.reconnectAttempts = this.maxReconnectAttempts; // 阻止自动重连
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * 获取连接状态
   */
  get connected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * 获取订阅的频道
   */
  get channels(): string[] {
    return Array.from(this.subscribedChannels);
  }
}

// 全局单例
let wsClient: WebSocketClient | null = null;

export function getWebSocketClient(): WebSocketClient {
  if (!wsClient) {
    wsClient = new WebSocketClient();
  }
  return wsClient;
}

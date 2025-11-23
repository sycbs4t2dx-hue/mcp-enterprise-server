import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Timeline,
  Progress,
  Alert,
  Badge,
  Tabs,
  List,
  Avatar,
  Statistic,
  Row,
  Col,
  Divider,
  Tooltip,
  Modal,
  Form,
  Input,
  Select,
  message,
  Empty,
  Descriptions,
  Steps
} from 'antd';
import {
  TeamOutlined,
  LockOutlined,
  UnlockOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  RobotOutlined,
  FileTextOutlined,
  CodeOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  BranchesOutlined,
  ApiOutlined,
  PartitionOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  UserOutlined
} from '@ant-design/icons';
import './CollaborationMonitor.css';

const { TabPane } = Tabs;
const { Option } = Select;
const { Step } = Steps;

interface AIAgent {
  agent_id: string;
  name: string;
  status: 'idle' | 'working' | 'waiting' | 'error';
  capabilities: string[];
  current_task?: string;
  progress: number;
  locks_held: string[];
  last_activity: string;
}

interface Lock {
  lock_id: string;
  agent_id: string;
  resource_id: string;
  resource_path: string;
  lock_type: 'file' | 'module' | 'global';
  lock_level: 'read' | 'write' | 'exclusive';
  status: 'active' | 'waiting' | 'expired';
  intent: string;
  acquired_at?: string;
  expires_at?: string;
  priority: number;
}

interface Task {
  task_id: string;
  task_type: string;
  description: string;
  status: 'pending' | 'assigned' | 'in_progress' | 'completed' | 'failed';
  assigned_to: string[];
  files: string[];
  dependencies: string[];
  progress: number;
  estimated_time: number;
  actual_time?: number;
  created_at: string;
  completed_at?: string;
}

interface Conflict {
  conflict_id: string;
  conflict_type: string;
  agents_involved: string[];
  resources: string[];
  description: string;
  severity: 'low' | 'medium' | 'high';
  suggested_resolution: string;
  resolved: boolean;
  detected_at: string;
  resolved_at?: string;
}

interface ActivityLog {
  id: string;
  timestamp: string;
  agent_id: string;
  action: string;
  resource?: string;
  status: 'success' | 'failure' | 'warning';
  message: string;
}

const CollaborationMonitor: React.FC = () => {
  const [agents, setAgents] = useState<AIAgent[]>([]);
  const [locks, setLocks] = useState<Lock[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<AIAgent | null>(null);
  const [agentModalVisible, setAgentModalVisible] = useState(false);
  const [taskModalVisible, setTaskModalVisible] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout>();

  // 加载协作状态
  const loadCollaborationStatus = async () => {
    try {
      // 加载代理状态
      const agentsResponse = await fetch('http://localhost:8765/api/collaborate/agents');
      if (agentsResponse.ok) {
        const agentsData = await agentsResponse.json();
        setAgents(agentsData.agents || []);
      }

      // 加载锁状态
      const locksResponse = await fetch('http://localhost:8765/api/collaborate/locks');
      if (locksResponse.ok) {
        const locksData = await locksResponse.json();
        setLocks(locksData.locks || []);
      }

      // 加载任务状态
      const tasksResponse = await fetch('http://localhost:8765/api/collaborate/tasks');
      if (tasksResponse.ok) {
        const tasksData = await tasksResponse.json();
        setTasks(tasksData.tasks || []);
      }

      // 加载冲突
      const conflictsResponse = await fetch('http://localhost:8765/api/collaborate/conflicts');
      if (conflictsResponse.ok) {
        const conflictsData = await conflictsResponse.json();
        setConflicts(conflictsData.conflicts || []);
      }

      // 加载活动日志
      const logsResponse = await fetch('http://localhost:8765/api/collaborate/activity');
      if (logsResponse.ok) {
        const logsData = await logsResponse.json();
        setActivityLogs(logsData.logs || []);
      }
    } catch (error) {
      console.error('Failed to load collaboration status:', error);
    }
  };

  useEffect(() => {
    loadCollaborationStatus();

    if (autoRefresh) {
      intervalRef.current = setInterval(loadCollaborationStatus, 5000); // 每5秒刷新
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh]);

  // 释放锁
  const releaseLock = async (lockId: string) => {
    try {
      const response = await fetch(`http://localhost:8765/api/collaborate/lock/${lockId}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        message.success('锁已释放');
        loadCollaborationStatus();
      }
    } catch (error) {
      message.error('释放锁失败');
    }
  };

  // 解决冲突
  const resolveConflict = async (conflictId: string) => {
    try {
      const response = await fetch(`http://localhost:8765/api/collaborate/conflicts/${conflictId}/resolve`, {
        method: 'POST'
      });
      if (response.ok) {
        message.success('冲突已解决');
        loadCollaborationStatus();
      }
    } catch (error) {
      message.error('解决冲突失败');
    }
  };

  // 代理状态标签
  const getAgentStatusTag = (status: string) => {
    const statusConfig: any = {
      'idle': { color: 'default', icon: <ClockCircleOutlined /> },
      'working': { color: 'processing', icon: <LoadingOutlined spin /> },
      'waiting': { color: 'warning', icon: <ExclamationCircleOutlined /> },
      'error': { color: 'error', icon: <CloseCircleOutlined /> }
    };
    const config = statusConfig[status] || statusConfig['idle'];
    return (
      <Tag color={config.color} icon={config.icon}>
        {status.toUpperCase()}
      </Tag>
    );
  };

  // 锁状态标签
  const getLockStatusTag = (status: string) => {
    const statusConfig: any = {
      'active': { color: 'success', icon: <LockOutlined /> },
      'waiting': { color: 'warning', icon: <ClockCircleOutlined /> },
      'expired': { color: 'error', icon: <CloseCircleOutlined /> }
    };
    const config = statusConfig[status] || statusConfig['active'];
    return (
      <Tag color={config.color} icon={config.icon}>
        {status.toUpperCase()}
      </Tag>
    );
  };

  // 任务状态标签
  const getTaskStatusTag = (status: string) => {
    const statusConfig: any = {
      'pending': { color: 'default', icon: <ClockCircleOutlined /> },
      'assigned': { color: 'processing', icon: <UserOutlined /> },
      'in_progress': { color: 'processing', icon: <LoadingOutlined spin /> },
      'completed': { color: 'success', icon: <CheckCircleOutlined /> },
      'failed': { color: 'error', icon: <CloseCircleOutlined /> }
    };
    const config = statusConfig[status] || statusConfig['pending'];
    return (
      <Tag color={config.color} icon={config.icon}>
        {status.toUpperCase()}
      </Tag>
    );
  };

  // 代理表格列
  const agentColumns = [
    {
      title: '代理',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: AIAgent) => (
        <Space>
          <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
          <a onClick={() => {
            setSelectedAgent(record);
            setAgentModalVisible(true);
          }}>
            {name}
          </a>
        </Space>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getAgentStatusTag(status)
    },
    {
      title: '当前任务',
      dataIndex: 'current_task',
      key: 'current_task',
      render: (task: string) => task || <span style={{ color: '#999' }}>无</span>
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => <Progress percent={progress} size="small" />
    },
    {
      title: '持有锁',
      dataIndex: 'locks_held',
      key: 'locks_held',
      render: (locks: string[]) => (
        <Badge count={locks.length} style={{ backgroundColor: locks.length > 0 ? '#52c41a' : '#d9d9d9' }} />
      )
    },
    {
      title: '能力',
      dataIndex: 'capabilities',
      key: 'capabilities',
      render: (caps: string[]) => (
        <Space size="small" wrap>
          {caps.map(cap => (
            <Tag key={cap} color="blue">{cap}</Tag>
          ))}
        </Space>
      )
    },
    {
      title: '最后活动',
      dataIndex: 'last_activity',
      key: 'last_activity',
      render: (time: string) => (
        <Tooltip title={time}>
          <span>{new Date(time).toLocaleTimeString()}</span>
        </Tooltip>
      )
    }
  ];

  // 锁表格列
  const lockColumns = [
    {
      title: '锁ID',
      dataIndex: 'lock_id',
      key: 'lock_id',
      render: (id: string) => <code>{id.substring(0, 8)}...</code>
    },
    {
      title: '持有者',
      dataIndex: 'agent_id',
      key: 'agent_id',
      render: (agentId: string) => {
        const agent = agents.find(a => a.agent_id === agentId);
        return agent ? agent.name : agentId;
      }
    },
    {
      title: '资源',
      dataIndex: 'resource_path',
      key: 'resource_path',
      render: (path: string) => (
        <Tooltip title={path}>
          <Space>
            <FileTextOutlined />
            <span>{path.split('/').pop()}</span>
          </Space>
        </Tooltip>
      )
    },
    {
      title: '类型',
      dataIndex: 'lock_type',
      key: 'lock_type',
      render: (type: string) => <Tag>{type}</Tag>
    },
    {
      title: '级别',
      dataIndex: 'lock_level',
      key: 'lock_level',
      render: (level: string) => {
        const color = level === 'exclusive' ? 'red' : level === 'write' ? 'orange' : 'green';
        return <Tag color={color}>{level}</Tag>;
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getLockStatusTag(status)
    },
    {
      title: '意图',
      dataIndex: 'intent',
      key: 'intent',
      ellipsis: true
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Lock) => (
        <Button
          type="link"
          danger
          size="small"
          icon={<UnlockOutlined />}
          onClick={() => releaseLock(record.lock_id)}
        >
          释放
        </Button>
      )
    }
  ];

  // 任务表格列
  const taskColumns = [
    {
      title: '任务',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '类型',
      dataIndex: 'task_type',
      key: 'task_type',
      render: (type: string) => <Tag>{type}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getTaskStatusTag(status)
    },
    {
      title: '分配给',
      dataIndex: 'assigned_to',
      key: 'assigned_to',
      render: (agentIds: string[]) => (
        <Avatar.Group maxCount={2}>
          {agentIds.map(id => {
            const agent = agents.find(a => a.agent_id === id);
            return (
              <Tooltip key={id} title={agent?.name || id}>
                <Avatar icon={<RobotOutlined />} />
              </Tooltip>
            );
          })}
        </Avatar.Group>
      )
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => <Progress percent={progress} size="small" />
    },
    {
      title: '文件',
      dataIndex: 'files',
      key: 'files',
      render: (files: string[]) => <Badge count={files.length} />
    },
    {
      title: '预计/实际时间',
      key: 'time',
      render: (_: any, record: Task) => (
        <span>
          {record.estimated_time}分钟
          {record.actual_time && ` / ${record.actual_time}分钟`}
        </span>
      )
    }
  ];

  return (
    <div className="collaboration-monitor">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃代理"
              value={agents.filter(a => a.status === 'working').length}
              suffix={`/ ${agents.length}`}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃锁"
              value={locks.filter(l => l.status === 'active').length}
              suffix={`/ ${locks.length}`}
              prefix={<LockOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="进行中任务"
              value={tasks.filter(t => t.status === 'in_progress').length}
              suffix={`/ ${tasks.length}`}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="未解决冲突"
              value={conflicts.filter(c => !c.resolved).length}
              prefix={<WarningOutlined />}
              valueStyle={{ color: conflicts.filter(c => !c.resolved).length > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 主卡片 */}
      <Card
        title={
          <Space>
            <TeamOutlined />
            <span>协作监控中心</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              type={autoRefresh ? 'primary' : 'default'}
              icon={<SyncOutlined spin={autoRefresh} />}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? '自动刷新中' : '开启自动刷新'}
            </Button>
            <Button icon={<SyncOutlined />} onClick={loadCollaborationStatus}>
              手动刷新
            </Button>
          </Space>
        }
      >
        <Tabs defaultActiveKey="agents">
          <TabPane
            tab={
              <span>
                <RobotOutlined />
                AI代理 ({agents.length})
              </span>
            }
            key="agents"
          >
            <Table
              dataSource={agents}
              columns={agentColumns}
              rowKey="agent_id"
              pagination={false}
            />
          </TabPane>

          <TabPane
            tab={
              <span>
                <LockOutlined />
                资源锁 ({locks.length})
              </span>
            }
            key="locks"
          >
            {locks.length > 0 ? (
              <Table
                dataSource={locks}
                columns={lockColumns}
                rowKey="lock_id"
                pagination={{ pageSize: 10 }}
              />
            ) : (
              <Empty description="当前没有活跃的锁" />
            )}
          </TabPane>

          <TabPane
            tab={
              <span>
                <CodeOutlined />
                任务队列 ({tasks.length})
              </span>
            }
            key="tasks"
          >
            {tasks.length > 0 ? (
              <Table
                dataSource={tasks}
                columns={taskColumns}
                rowKey="task_id"
                pagination={{ pageSize: 10 }}
              />
            ) : (
              <Empty description="当前没有任务" />
            )}
          </TabPane>

          <TabPane
            tab={
              <Badge
                count={conflicts.filter(c => !c.resolved).length}
                dot={conflicts.filter(c => !c.resolved).length > 0}
              >
                <span>
                  <WarningOutlined />
                  冲突检测
                </span>
              </Badge>
            }
            key="conflicts"
          >
            {conflicts.length > 0 ? (
              <List
                dataSource={conflicts}
                renderItem={conflict => (
                  <List.Item
                    actions={[
                      !conflict.resolved && (
                        <Button
                          type="primary"
                          size="small"
                          onClick={() => resolveConflict(conflict.conflict_id)}
                        >
                          解决
                        </Button>
                      )
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          style={{
                            backgroundColor: conflict.resolved ? '#52c41a' :
                              conflict.severity === 'high' ? '#ff4d4f' :
                                conflict.severity === 'medium' ? '#faad14' : '#d9d9d9'
                          }}
                          icon={conflict.resolved ? <CheckCircleOutlined /> : <WarningOutlined />}
                        />
                      }
                      title={
                        <Space>
                          {conflict.description}
                          <Tag color={conflict.severity === 'high' ? 'red' :
                            conflict.severity === 'medium' ? 'orange' : 'default'}>
                            {conflict.severity.toUpperCase()}
                          </Tag>
                          {conflict.resolved && <Tag color="success">已解决</Tag>}
                        </Space>
                      }
                      description={
                        <div>
                          <p>涉及代理: {conflict.agents_involved.join(', ')}</p>
                          <p>资源: {conflict.resources.join(', ')}</p>
                          <p>建议解决方案: {conflict.suggested_resolution}</p>
                          <p>
                            检测时间: {new Date(conflict.detected_at).toLocaleString()}
                            {conflict.resolved_at && ` | 解决时间: ${new Date(conflict.resolved_at).toLocaleString()}`}
                          </p>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="没有检测到冲突" />
            )}
          </TabPane>

          <TabPane
            tab={
              <span>
                <ClockCircleOutlined />
                活动日志
              </span>
            }
            key="logs"
          >
            <Timeline mode="left">
              {activityLogs.slice(0, 20).map(log => (
                <Timeline.Item
                  key={log.id}
                  color={log.status === 'success' ? 'green' :
                    log.status === 'failure' ? 'red' : 'orange'}
                  label={new Date(log.timestamp).toLocaleTimeString()}
                >
                  <Space>
                    <Tag>{agents.find(a => a.agent_id === log.agent_id)?.name || log.agent_id}</Tag>
                    <span>{log.action}</span>
                    {log.resource && <code>{log.resource}</code>}
                  </Space>
                  <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
                    {log.message}
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
          </TabPane>

          <TabPane
            tab={
              <span>
                <PartitionOutlined />
                协作图谱
              </span>
            }
            key="graph"
          >
            <Card>
              <div style={{ textAlign: 'center', padding: 40 }}>
                <BranchesOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                <p style={{ marginTop: 16 }}>协作关系可视化</p>
                <p style={{ color: '#999' }}>
                  显示代理间的协作关系、资源依赖和任务流
                </p>
              </div>
            </Card>
          </TabPane>
        </Tabs>
      </Card>

      {/* 代理详情Modal */}
      <Modal
        title={`代理详情: ${selectedAgent?.name}`}
        visible={agentModalVisible}
        onCancel={() => setAgentModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedAgent && (
          <div>
            <Descriptions bordered column={1}>
              <Descriptions.Item label="ID">{selectedAgent.agent_id}</Descriptions.Item>
              <Descriptions.Item label="状态">
                {getAgentStatusTag(selectedAgent.status)}
              </Descriptions.Item>
              <Descriptions.Item label="当前任务">
                {selectedAgent.current_task || '无'}
              </Descriptions.Item>
              <Descriptions.Item label="进度">
                <Progress percent={selectedAgent.progress} />
              </Descriptions.Item>
              <Descriptions.Item label="能力">
                <Space wrap>
                  {selectedAgent.capabilities.map(cap => (
                    <Tag key={cap} color="blue">{cap}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="持有锁">
                {selectedAgent.locks_held.length > 0 ? (
                  <List
                    size="small"
                    dataSource={selectedAgent.locks_held}
                    renderItem={lockId => {
                      const lock = locks.find(l => l.lock_id === lockId);
                      return (
                        <List.Item>
                          <Space>
                            <LockOutlined />
                            <span>{lock?.resource_path || lockId}</span>
                            {lock && getLockStatusTag(lock.status)}
                          </Space>
                        </List.Item>
                      );
                    }}
                  />
                ) : '无'}
              </Descriptions.Item>
              <Descriptions.Item label="最后活动">
                {new Date(selectedAgent.last_activity).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Card title="任务历史" size="small">
              <Timeline>
                {tasks
                  .filter(t => t.assigned_to.includes(selectedAgent.agent_id))
                  .map(task => (
                    <Timeline.Item
                      key={task.task_id}
                      color={task.status === 'completed' ? 'green' :
                        task.status === 'failed' ? 'red' : 'blue'}
                    >
                      <Space>
                        {getTaskStatusTag(task.status)}
                        <span>{task.description}</span>
                      </Space>
                    </Timeline.Item>
                  ))}
              </Timeline>
            </Card>
          </div>
        )}
      </Modal>

      {/* 新建任务Modal */}
      <Modal
        title="创建协作任务"
        visible={taskModalVisible}
        onCancel={() => setTaskModalVisible(false)}
        footer={null}
      >
        <Form
          layout="vertical"
          onFinish={async (values) => {
            try {
              const response = await fetch('http://localhost:8765/api/collaborate/task/assign', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(values)
              });
              if (response.ok) {
                message.success('任务创建成功');
                setTaskModalVisible(false);
                loadCollaborationStatus();
              }
            } catch (error) {
              message.error('任务创建失败');
            }
          }}
        >
          <Form.Item
            label="任务描述"
            name="description"
            rules={[{ required: true }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item
            label="任务类型"
            name="task_type"
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="coding">编码</Option>
              <Option value="testing">测试</Option>
              <Option value="review">审查</Option>
              <Option value="documentation">文档</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="分配给"
            name="agent_ids"
            rules={[{ required: true }]}
          >
            <Select mode="multiple">
              {agents.map(agent => (
                <Option key={agent.agent_id} value={agent.agent_id}>
                  {agent.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="涉及文件"
            name="files"
          >
            <Select mode="tags" placeholder="输入文件路径">
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">创建</Button>
              <Button onClick={() => setTaskModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CollaborationMonitor;
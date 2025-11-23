import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Space,
  Select,
  DatePicker,
  Button,
  Timeline,
  List,
  Avatar,
  Tooltip,
  Badge,
  Tabs,
  Alert,
  Empty
} from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  PieChartOutlined,
  RiseOutlined,
  FallOutlined,
  TrophyOutlined,
  BulbOutlined,
  ClockCircleOutlined,
  CodeOutlined,
  TeamOutlined,
  FireOutlined,
  ThunderboltOutlined,
  BugOutlined,
  ToolOutlined,
  FileAddOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  RocketOutlined,
  BookOutlined
} from '@ant-design/icons';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';
import './LearningDashboard.css';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { TabPane } = Tabs;

interface LearningMetrics {
  total_sessions: number;
  total_patterns: number;
  total_experiences: number;
  average_effectiveness: number;
  average_success_rate: number;
  time_saved_total: number;
  bugs_fixed_total: number;
  bugs_introduced_total: number;
  code_quality_improvement: number;
  learning_velocity: number;
}

interface SessionTrend {
  date: string;
  sessions: number;
  patterns: number;
  effectiveness: number;
}

interface CategoryDistribution {
  category: string;
  count: number;
  percentage: number;
}

interface SkillRadar {
  skill: string;
  current: number;
  previous: number;
}

interface TopPattern {
  pattern_name: string;
  usage_count: number;
  effectiveness: number;
  evolution_stage: number;
}

interface RecentSession {
  session_id: string;
  context_type: string;
  problem_description: string;
  time_spent: number;
  lines_changed: number;
  effectiveness: number;
  created_at: string;
}

const LearningDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<LearningMetrics | null>(null);
  const [sessionTrends, setSessionTrends] = useState<SessionTrend[]>([]);
  const [categoryDistribution, setCategoryDistribution] = useState<CategoryDistribution[]>([]);
  const [skillRadarData, setSkillRadarData] = useState<SkillRadar[]>([]);
  const [topPatterns, setTopPatterns] = useState<TopPattern[]>([]);
  const [recentSessions, setRecentSessions] = useState<RecentSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState<string>('week');
  const [projectId, setProjectId] = useState<string>('default');

  // 加载仪表板数据
  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // 加载总体指标
      const metricsResponse = await fetch(`http://localhost:8765/api/evolution/metrics?project_id=${projectId}&range=${timeRange}`);
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData);
      }

      // 加载趋势数据
      const trendsResponse = await fetch(`http://localhost:8765/api/evolution/trends?project_id=${projectId}&range=${timeRange}`);
      if (trendsResponse.ok) {
        const trendsData = await trendsResponse.json();
        setSessionTrends(trendsData.trends || []);
      }

      // 加载分布数据
      const distributionResponse = await fetch(`http://localhost:8765/api/evolution/distribution?project_id=${projectId}`);
      if (distributionResponse.ok) {
        const distributionData = await distributionResponse.json();
        setCategoryDistribution(distributionData.categories || []);
      }

      // 加载技能雷达图数据
      const skillsResponse = await fetch(`http://localhost:8765/api/evolution/skills?project_id=${projectId}`);
      if (skillsResponse.ok) {
        const skillsData = await skillsResponse.json();
        setSkillRadarData(skillsData.skills || []);
      }

      // 加载热门模式
      const patternsResponse = await fetch(`http://localhost:8765/api/evolution/top-patterns?project_id=${projectId}&limit=10`);
      if (patternsResponse.ok) {
        const patternsData = await patternsResponse.json();
        setTopPatterns(patternsData.patterns || []);
      }

      // 加载最近会话
      const sessionsResponse = await fetch(`http://localhost:8765/api/evolution/recent-sessions?project_id=${projectId}&limit=10`);
      if (sessionsResponse.ok) {
        const sessionsData = await sessionsResponse.json();
        setRecentSessions(sessionsData.sessions || []);
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [projectId, timeRange]);

  // 模拟数据（实际应从API获取）
  useEffect(() => {
    if (!metrics) {
      setMetrics({
        total_sessions: 156,
        total_patterns: 42,
        total_experiences: 89,
        average_effectiveness: 0.78,
        average_success_rate: 0.85,
        time_saved_total: 1250,
        bugs_fixed_total: 234,
        bugs_introduced_total: 12,
        code_quality_improvement: 0.65,
        learning_velocity: 3.2
      });

      setSessionTrends([
        { date: '2025-11-14', sessions: 12, patterns: 3, effectiveness: 0.75 },
        { date: '2025-11-15', sessions: 15, patterns: 5, effectiveness: 0.78 },
        { date: '2025-11-16', sessions: 18, patterns: 4, effectiveness: 0.80 },
        { date: '2025-11-17', sessions: 14, patterns: 6, effectiveness: 0.82 },
        { date: '2025-11-18', sessions: 20, patterns: 7, effectiveness: 0.85 },
        { date: '2025-11-19', sessions: 22, patterns: 8, effectiveness: 0.87 },
        { date: '2025-11-20', sessions: 25, patterns: 9, effectiveness: 0.89 }
      ]);

      setCategoryDistribution([
        { category: 'Bug修复', count: 45, percentage: 28.8 },
        { category: '功能开发', count: 38, percentage: 24.4 },
        { category: '代码优化', count: 32, percentage: 20.5 },
        { category: '重构', count: 25, percentage: 16.0 },
        { category: '测试', count: 16, percentage: 10.3 }
      ]);

      setSkillRadarData([
        { skill: '问题解决', current: 85, previous: 70 },
        { skill: '代码质量', current: 78, previous: 65 },
        { skill: '性能优化', current: 72, previous: 60 },
        { skill: '架构设计', current: 68, previous: 55 },
        { skill: '测试覆盖', current: 75, previous: 68 },
        { skill: '文档编写', current: 65, previous: 50 }
      ]);
    }
  }, [metrics]);

  // 饼图颜色
  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  return (
    <div className="learning-dashboard">
      {/* 页头 */}
      <Card style={{ marginBottom: 24 }}>
        <Row align="middle" justify="space-between">
          <Col>
            <Space size="large">
              <DashboardOutlined style={{ fontSize: 32, color: '#1890ff' }} />
              <div>
                <h2 style={{ margin: 0 }}>智能学习仪表板</h2>
                <p style={{ margin: 0, color: '#999' }}>
                  跟踪AI编码能力的成长与进化
                </p>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              <Select
                value={projectId}
                onChange={setProjectId}
                style={{ width: 150 }}
              >
                <Option value="default">默认项目</Option>
                <Option value="project1">项目 1</Option>
                <Option value="project2">项目 2</Option>
              </Select>
              <Select
                value={timeRange}
                onChange={setTimeRange}
                style={{ width: 120 }}
              >
                <Option value="day">今天</Option>
                <Option value="week">本周</Option>
                <Option value="month">本月</Option>
                <Option value="quarter">本季度</Option>
                <Option value="year">本年</Option>
              </Select>
              <Button icon={<SyncOutlined />} onClick={loadDashboardData}>
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 核心指标 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="学习会话"
              value={metrics?.total_sessions || 0}
              prefix={<BookOutlined />}
              suffix="次"
              valueStyle={{ color: '#1890ff' }}
            />
            <div style={{ marginTop: 8 }}>
              <Progress percent={75} size="small" showInfo={false} />
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="平均有效性"
              value={(metrics?.average_effectiveness || 0) * 100}
              precision={1}
              prefix={<TrophyOutlined />}
              suffix="%"
              valueStyle={{ color: '#52c41a' }}
            />
            <div style={{ marginTop: 8 }}>
              <span style={{ color: '#52c41a' }}>
                <RiseOutlined /> 12.3%
              </span>
              <span style={{ marginLeft: 8, color: '#999' }}>vs 上周</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="节省时间"
              value={metrics?.time_saved_total || 0}
              prefix={<ClockCircleOutlined />}
              suffix="分钟"
              valueStyle={{ color: '#faad14' }}
            />
            <div style={{ marginTop: 8 }}>
              <span>相当于 {((metrics?.time_saved_total || 0) / 60).toFixed(1)} 小时</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="学习速度"
              value={metrics?.learning_velocity || 0}
              precision={1}
              prefix={<RocketOutlined />}
              suffix="倍"
              valueStyle={{ color: '#eb2f96' }}
            />
            <div style={{ marginTop: 8 }}>
              <Progress
                percent={Math.min((metrics?.learning_velocity || 0) * 20, 100)}
                size="small"
                strokeColor="#eb2f96"
                showInfo={false}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* 图表区域 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <LineChartOutlined />
                <span>学习趋势</span>
              </Space>
            }
          >
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={sessionTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <ChartTooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="sessions"
                  name="会话数"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.6}
                />
                <Area
                  type="monotone"
                  dataKey="patterns"
                  name="模式数"
                  stroke="#82ca9d"
                  fill="#82ca9d"
                  fillOpacity={0.6}
                />
                <Line
                  type="monotone"
                  dataKey="effectiveness"
                  name="有效性"
                  stroke="#ff7c7c"
                  strokeWidth={2}
                  yAxisId="right"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card
            title={
              <Space>
                <PieChartOutlined />
                <span>类别分布</span>
              </Space>
            }
          >
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percentage }) => `${name}: ${percentage}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {categoryDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <ChartTooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <BarChartOutlined />
                <span>技能成长雷达</span>
              </Space>
            }
          >
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={skillRadarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="skill" />
                <PolarRadiusAxis angle={90} domain={[0, 100]} />
                <Radar
                  name="当前水平"
                  dataKey="current"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.6}
                />
                <Radar
                  name="之前水平"
                  dataKey="previous"
                  stroke="#82ca9d"
                  fill="#82ca9d"
                  fillOpacity={0.3}
                />
                <Legend />
                <ChartTooltip />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <ExperimentOutlined />
                <span>质量指标</span>
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="修复Bug"
                    value={metrics?.bugs_fixed_total || 0}
                    prefix={<BugOutlined />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                  <Progress
                    percent={85}
                    size="small"
                    strokeColor="#52c41a"
                    format={() => '修复率'}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="引入Bug"
                    value={metrics?.bugs_introduced_total || 0}
                    prefix={<ExclamationCircleOutlined />}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                  <Progress
                    percent={15}
                    size="small"
                    strokeColor="#ff4d4f"
                    format={() => '引入率'}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="成功率"
                    value={(metrics?.average_success_rate || 0) * 100}
                    precision={1}
                    suffix="%"
                    prefix={<CheckCircleOutlined />}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="代码质量"
                    value={(metrics?.code_quality_improvement || 0) * 100}
                    precision={1}
                    suffix="%"
                    prefix={<CodeOutlined />}
                    valueStyle={{ color: '#722ed1' }}
                  />
                </Card>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* 详细信息标签页 */}
      <Card style={{ marginTop: 24 }}>
        <Tabs defaultActiveKey="patterns">
          <TabPane
            tab={
              <span>
                <FireOutlined />
                热门模式
              </span>
            }
            key="patterns"
          >
            <Table
              dataSource={topPatterns}
              rowKey="pattern_name"
              pagination={{ pageSize: 5 }}
              columns={[
                {
                  title: '模式名称',
                  dataIndex: 'pattern_name',
                  key: 'pattern_name',
                  render: (name: string) => (
                    <Space>
                      <CodeOutlined />
                      <span>{name}</span>
                    </Space>
                  )
                },
                {
                  title: '使用次数',
                  dataIndex: 'usage_count',
                  key: 'usage_count',
                  sorter: (a, b) => a.usage_count - b.usage_count,
                  render: (count: number) => <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
                },
                {
                  title: '有效性',
                  dataIndex: 'effectiveness',
                  key: 'effectiveness',
                  render: (effectiveness: number) => (
                    <Progress percent={Math.round(effectiveness * 100)} size="small" />
                  )
                },
                {
                  title: '演化阶段',
                  dataIndex: 'evolution_stage',
                  key: 'evolution_stage',
                  render: (stage: number) => (
                    <Tag color={stage > 3 ? 'green' : stage > 1 ? 'blue' : 'default'}>
                      阶段 {stage}
                    </Tag>
                  )
                }
              ]}
            />
          </TabPane>

          <TabPane
            tab={
              <span>
                <ClockCircleOutlined />
                最近会话
              </span>
            }
            key="sessions"
          >
            <Timeline mode="left">
              {recentSessions.map(session => (
                <Timeline.Item
                  key={session.session_id}
                  label={new Date(session.created_at).toLocaleString()}
                  color={session.effectiveness > 0.8 ? 'green' : session.effectiveness > 0.6 ? 'blue' : 'gray'}
                >
                  <Card size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space>
                        <Tag>{session.context_type}</Tag>
                        <span>{session.problem_description}</span>
                      </Space>
                      <Row gutter={[16, 0]}>
                        <Col>
                          <ClockCircleOutlined /> {session.time_spent}分钟
                        </Col>
                        <Col>
                          <CodeOutlined /> {session.lines_changed}行
                        </Col>
                        <Col>
                          <TrophyOutlined /> {(session.effectiveness * 100).toFixed(0)}%
                        </Col>
                      </Row>
                    </Space>
                  </Card>
                </Timeline.Item>
              ))}
            </Timeline>
          </TabPane>

          <TabPane
            tab={
              <span>
                <BulbOutlined />
                学习洞察
              </span>
            }
            key="insights"
          >
            <List
              itemLayout="horizontal"
              dataSource={[
                {
                  title: '最擅长领域',
                  description: '您在Bug修复方面表现最佳，成功率达到92%',
                  icon: <TrophyOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                },
                {
                  title: '成长最快',
                  description: '性能优化技能提升最快，较上月提高了35%',
                  icon: <RiseOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                },
                {
                  title: '建议关注',
                  description: '测试覆盖率偏低，建议加强单元测试的学习',
                  icon: <ExclamationCircleOutlined style={{ fontSize: 24, color: '#faad14' }} />
                },
                {
                  title: '里程碑',
                  description: '恭喜！您已累计解决超过200个问题',
                  icon: <FireOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />
                }
              ]}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<Avatar>{item.icon}</Avatar>}
                    title={item.title}
                    description={item.description}
                  />
                </List.Item>
              )}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 底部提示 */}
      <Alert
        message="学习建议"
        description={
          <div>
            <p>基于您的学习数据分析：</p>
            <ul style={{ marginBottom: 0 }}>
              <li>继续保持在Bug修复方面的优秀表现</li>
              <li>建议增加代码重构相关的学习，这将显著提升代码质量</li>
              <li>可以尝试更多复杂的性能优化场景，进一步提升技能</li>
            </ul>
          </div>
        }
        type="info"
        showIcon
        style={{ marginTop: 24 }}
      />
    </div>
  );
};

export default LearningDashboard;
import React, { useState, useEffect } from 'react';
import {
  Card,
  List,
  Tag,
  Space,
  Button,
  Input,
  Select,
  Drawer,
  Descriptions,
  Row,
  Col,
  Progress,
  Alert,
  Badge,
  Tabs,
  Timeline,
  Statistic,
  Rate,
  Avatar,
  Comment,
  Form,
  message,
  Tooltip,
  Empty,
  Divider,
  Modal
} from 'antd';
import {
  BookOutlined,
  ShareAltOutlined,
  LikeOutlined,
  DislikeOutlined,
  MessageOutlined,
  ClockCircleOutlined,
  TrophyOutlined,
  FireOutlined,
  TeamOutlined,
  RocketOutlined,
  BulbOutlined,
  ExperimentOutlined,
  SyncOutlined,
  StarOutlined,
  ForkOutlined,
  PlusOutlined,
  SearchOutlined,
  FilterOutlined,
  ExportOutlined
} from '@ant-design/icons';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './ExperienceHub.css';

const { Search } = Input;
const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;

interface Experience {
  experience_id: string;
  experience_type: string;
  category: string;
  title: string;
  description: string;
  problem: string;
  solution: string;
  code_example?: string;
  context: any;
  prerequisites: string[];
  limitations: string[];
  effectiveness: number;
  complexity: number;
  reusability: number;
  reliability: number;
  usage_count: number;
  success_count: number;
  failure_count: number;
  average_time_saved: number;
  ratings: number[];
  comments: string[];
  improvements: string[];
  related_experiences: string[];
  tags: string[];
  keywords: string[];
  project_id?: string;
  author_id?: string;
  created_at: string;
  updated_at: string;
  version: number;
}

interface ExperienceRecommendation {
  experience: Experience;
  relevance_score: number;
  confidence: number;
  reasoning: string;
  expected_benefit: {
    time_saved: number;
    success_probability: number;
    quality_improvement: number;
    reusability: number;
  };
  risk_assessment: {
    compatibility: number;
    complexity: number;
    reliability: number;
  };
}

const ExperienceHub: React.FC = () => {
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [recommendations, setRecommendations] = useState<ExperienceRecommendation[]>([]);
  const [selectedExperience, setSelectedExperience] = useState<Experience | null>(null);
  const [loading, setLoading] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [feedbackModalVisible, setFeedbackModalVisible] = useState(false);

  // 筛选状态
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('effectiveness');
  const [currentTab, setCurrentTab] = useState<string>('browse');

  // 加载经验
  const loadExperiences = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8765/api/experiences');
      if (response.ok) {
        const data = await response.json();
        setExperiences(data.experiences || []);
      }
    } catch (error) {
      console.error('Failed to load experiences:', error);
      message.error('加载经验失败');
    } finally {
      setLoading(false);
    }
  };

  // 搜索经验
  const searchExperiences = async () => {
    if (!searchQuery) return;

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8765/api/evolution/suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context_type: selectedType === 'all' ? 'general' : selectedType,
          problem: searchQuery,
          files: [],
          top_k: 10
        })
      });

      if (response.ok) {
        const data = await response.json();
        setRecommendations(data.suggestions || []);
        setCurrentTab('recommendations');
      }
    } catch (error) {
      console.error('Search failed:', error);
      message.error('搜索失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExperiences();
  }, []);

  // 排序经验
  const sortedExperiences = [...experiences].sort((a, b) => {
    switch (sortBy) {
      case 'effectiveness':
        return b.effectiveness - a.effectiveness;
      case 'usage':
        return b.usage_count - a.usage_count;
      case 'reusability':
        return b.reusability - a.reusability;
      case 'recent':
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      default:
        return 0;
    }
  });

  // 过滤经验
  const filteredExperiences = sortedExperiences.filter(exp => {
    if (selectedCategory !== 'all' && exp.category !== selectedCategory) return false;
    if (selectedType !== 'all' && exp.experience_type !== selectedType) return false;
    return true;
  });

  // 分享经验
  const shareExperience = async (experienceId: string, targetProject: string) => {
    try {
      const response = await fetch(`http://localhost:8765/api/experiences/${experienceId}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_project: targetProject })
      });

      if (response.ok) {
        message.success('经验共享成功');
        setShareModalVisible(false);
      }
    } catch (error) {
      message.error('共享失败');
    }
  };

  // 提供反馈
  const submitFeedback = async (experienceId: string, feedback: any) => {
    try {
      const response = await fetch(`http://localhost:8765/api/experiences/${experienceId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedback)
      });

      if (response.ok) {
        message.success('反馈提交成功');
        setFeedbackModalVisible(false);
        loadExperiences();
      }
    } catch (error) {
      message.error('提交失败');
    }
  };

  // 经验卡片
  const ExperienceCard: React.FC<{ exp: Experience }> = ({ exp }) => (
    <Card
      hoverable
      style={{ marginBottom: 16 }}
      onClick={() => {
        setSelectedExperience(exp);
        setDrawerVisible(true);
      }}
      actions={[
        <Tooltip title="有效性">
          <Space>
            <TrophyOutlined />
            {(exp.effectiveness * 100).toFixed(0)}%
          </Space>
        </Tooltip>,
        <Tooltip title="使用次数">
          <Space>
            <TeamOutlined />
            {exp.usage_count}
          </Space>
        </Tooltip>,
        <Tooltip title="平均节省时间">
          <Space>
            <ClockCircleOutlined />
            {exp.average_time_saved}分钟
          </Space>
        </Tooltip>
      ]}
    >
      <Card.Meta
        avatar={
          <Avatar
            style={{
              backgroundColor: exp.effectiveness > 0.8 ? '#52c41a' :
                exp.effectiveness > 0.6 ? '#1890ff' : '#faad14'
            }}
            icon={<BulbOutlined />}
          />
        }
        title={
          <Space>
            {exp.title}
            {exp.version > 1 && <Badge count={`v${exp.version}`} />}
          </Space>
        }
        description={
          <div>
            <p>{exp.description}</p>
            <Space wrap>
              <Tag color="blue">{exp.experience_type}</Tag>
              <Tag color="green">{exp.category}</Tag>
              {exp.tags.slice(0, 3).map(tag => (
                <Tag key={tag}>{tag}</Tag>
              ))}
              {exp.tags.length > 3 && <Tag>+{exp.tags.length - 3}</Tag>}
            </Space>
          </div>
        }
      />

      <div style={{ marginTop: 16 }}>
        <Row gutter={[16, 0]}>
          <Col span={6}>
            <Progress
              type="circle"
              percent={Math.round(exp.reusability * 100)}
              width={50}
              format={() => '可复用'}
            />
          </Col>
          <Col span={6}>
            <Progress
              type="circle"
              percent={Math.round(exp.reliability * 100)}
              width={50}
              format={() => '可靠性'}
            />
          </Col>
          <Col span={6}>
            <Progress
              type="circle"
              percent={Math.round((1 - exp.complexity) * 100)}
              width={50}
              format={() => '简单度'}
            />
          </Col>
          <Col span={6}>
            <div style={{ textAlign: 'center' }}>
              <Rate
                disabled
                defaultValue={exp.ratings.length > 0 ?
                  exp.ratings.reduce((a, b) => a + b, 0) / exp.ratings.length : 0}
                style={{ fontSize: 12 }}
              />
              <div style={{ fontSize: 10, color: '#999' }}>
                {exp.ratings.length} 评价
              </div>
            </div>
          </Col>
        </Row>
      </div>
    </Card>
  );

  // 推荐卡片
  const RecommendationCard: React.FC<{ rec: ExperienceRecommendation }> = ({ rec }) => (
    <Card
      hoverable
      style={{ marginBottom: 16 }}
      onClick={() => {
        setSelectedExperience(rec.experience);
        setDrawerVisible(true);
      }}
    >
      <Alert
        message={`相关性: ${(rec.relevance_score * 100).toFixed(0)}% | 置信度: ${(rec.confidence * 100).toFixed(0)}%`}
        description={rec.reasoning}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Card.Meta
        title={rec.experience.title}
        description={rec.experience.description}
      />

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card size="small" title="预期收益">
            <div>节省时间: {rec.expected_benefit.time_saved}分钟</div>
            <div>成功概率: {(rec.expected_benefit.success_probability * 100).toFixed(0)}%</div>
            <div>质量提升: {(rec.expected_benefit.quality_improvement * 100).toFixed(0)}%</div>
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="风险评估">
            <div>兼容性: {(rec.risk_assessment.compatibility * 100).toFixed(0)}%</div>
            <div>复杂度: {(rec.risk_assessment.complexity * 100).toFixed(0)}%</div>
            <div>可靠性风险: {(rec.risk_assessment.reliability * 100).toFixed(0)}%</div>
          </Card>
        </Col>
      </Row>
    </Card>
  );

  return (
    <div className="experience-hub">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总经验数"
              value={experiences.length}
              prefix={<BookOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均有效性"
              value={experiences.length > 0 ?
                (experiences.reduce((sum, e) => sum + e.effectiveness, 0) / experiences.length * 100) : 0}
              precision={1}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总使用次数"
              value={experiences.reduce((sum, e) => sum + e.usage_count, 0)}
              prefix={<FireOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="时间节省"
              value={experiences.reduce((sum, e) => sum + e.average_time_saved * e.usage_count, 0)}
              suffix="分钟"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 主卡片 */}
      <Card
        title={
          <Space>
            <BookOutlined />
            <span>经验中心</span>
          </Space>
        }
      >
        {/* 搜索和筛选 */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Search
            placeholder="搜索经验或描述问题..."
            style={{ width: 300 }}
            enterButton={<><SearchOutlined /> 智能搜索</>}
            onSearch={() => searchExperiences()}
            onChange={e => setSearchQuery(e.target.value)}
            value={searchQuery}
          />

          <Select
            style={{ width: 150 }}
            placeholder="类别"
            value={selectedCategory}
            onChange={setSelectedCategory}
          >
            <Option value="all">全部类别</Option>
            <Option value="bug_fix">Bug修复</Option>
            <Option value="optimization">优化</Option>
            <Option value="refactor">重构</Option>
            <Option value="feature">功能</Option>
          </Select>

          <Select
            style={{ width: 150 }}
            placeholder="类型"
            value={selectedType}
            onChange={setSelectedType}
          >
            <Option value="all">全部类型</Option>
            <Option value="solution">解决方案</Option>
            <Option value="pattern">模式</Option>
            <Option value="trick">技巧</Option>
            <Option value="pitfall">陷阱</Option>
          </Select>

          <Select
            style={{ width: 150 }}
            placeholder="排序"
            value={sortBy}
            onChange={setSortBy}
          >
            <Option value="effectiveness">按有效性</Option>
            <Option value="usage">按使用次数</Option>
            <Option value="reusability">按可复用性</Option>
            <Option value="recent">按更新时间</Option>
          </Select>

          <Button icon={<SyncOutlined />} onClick={loadExperiences}>
            刷新
          </Button>
        </Space>

        {/* 标签页 */}
        <Tabs activeKey={currentTab} onChange={setCurrentTab}>
          <TabPane
            tab={
              <span>
                <BookOutlined />
                浏览经验
              </span>
            }
            key="browse"
          >
            <List
              grid={{ gutter: 16, xs: 1, sm: 1, md: 2, lg: 2, xl: 3, xxl: 3 }}
              dataSource={filteredExperiences}
              loading={loading}
              renderItem={exp => (
                <List.Item>
                  <ExperienceCard exp={exp} />
                </List.Item>
              )}
              pagination={{
                pageSize: 9,
                showSizeChanger: true
              }}
            />
          </TabPane>

          <TabPane
            tab={
              <span>
                <BulbOutlined />
                智能推荐
              </span>
            }
            key="recommendations"
          >
            {recommendations.length > 0 ? (
              <List
                dataSource={recommendations}
                loading={loading}
                renderItem={rec => (
                  <List.Item>
                    <RecommendationCard rec={rec} />
                  </List.Item>
                )}
              />
            ) : (
              <Empty
                description="输入问题描述以获取智能推荐"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </TabPane>

          <TabPane
            tab={
              <span>
                <ShareAltOutlined />
                我的共享
              </span>
            }
            key="shared"
          >
            <Empty description="暂无共享经验" />
          </TabPane>

          <TabPane
            tab={
              <span>
                <StarOutlined />
                收藏夹
              </span>
            }
            key="favorites"
          >
            <Empty description="暂无收藏" />
          </TabPane>
        </Tabs>
      </Card>

      {/* 经验详情抽屉 */}
      <Drawer
        title={selectedExperience?.title}
        placement="right"
        width={800}
        onClose={() => setDrawerVisible(false)}
        visible={drawerVisible}
        extra={
          <Space>
            <Button
              icon={<ShareAltOutlined />}
              onClick={() => setShareModalVisible(true)}
            >
              共享
            </Button>
            <Button
              icon={<MessageOutlined />}
              onClick={() => setFeedbackModalVisible(true)}
            >
              反馈
            </Button>
            <Button icon={<ExportOutlined />}>导出</Button>
          </Space>
        }
      >
        {selectedExperience && (
          <div>
            <Descriptions bordered column={1} style={{ marginBottom: 24 }}>
              <Descriptions.Item label="类型">
                <Tag>{selectedExperience.experience_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="类别">
                <Tag>{selectedExperience.category}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="问题">
                {selectedExperience.problem}
              </Descriptions.Item>
              <Descriptions.Item label="解决方案">
                {selectedExperience.solution}
              </Descriptions.Item>
              <Descriptions.Item label="前置条件">
                {selectedExperience.prerequisites.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {selectedExperience.prerequisites.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                ) : '无'}
              </Descriptions.Item>
              <Descriptions.Item label="限制">
                {selectedExperience.limitations.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {selectedExperience.limitations.map((l, i) => (
                      <li key={i}>{l}</li>
                    ))}
                  </ul>
                ) : '无'}
              </Descriptions.Item>
              <Descriptions.Item label="标签">
                <Space wrap>
                  {selectedExperience.tags.map(tag => (
                    <Tag key={tag}>{tag}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <Tabs defaultActiveKey="code">
              <TabPane tab="代码示例" key="code">
                {selectedExperience.code_example ? (
                  <SyntaxHighlighter
                    language="python"
                    style={vscDarkPlus}
                    showLineNumbers
                  >
                    {selectedExperience.code_example}
                  </SyntaxHighlighter>
                ) : (
                  <Empty description="暂无代码示例" />
                )}
              </TabPane>

              <TabPane tab="使用统计" key="stats">
                <Row gutter={[16, 16]}>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="使用次数"
                        value={selectedExperience.usage_count}
                        prefix={<TeamOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="成功率"
                        value={(selectedExperience.success_count /
                          Math.max(1, selectedExperience.usage_count) * 100)}
                        precision={1}
                        suffix="%"
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="平均节省"
                        value={selectedExperience.average_time_saved}
                        suffix="分钟"
                        prefix={<ClockCircleOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>

                <Card style={{ marginTop: 16 }} title="效果指标">
                  <div style={{ padding: '0 24px' }}>
                    <div style={{ marginBottom: 16 }}>
                      <span>有效性</span>
                      <Progress percent={Math.round(selectedExperience.effectiveness * 100)} />
                    </div>
                    <div style={{ marginBottom: 16 }}>
                      <span>可复用性</span>
                      <Progress
                        percent={Math.round(selectedExperience.reusability * 100)}
                        strokeColor="#52c41a"
                      />
                    </div>
                    <div style={{ marginBottom: 16 }}>
                      <span>可靠性</span>
                      <Progress
                        percent={Math.round(selectedExperience.reliability * 100)}
                        strokeColor="#1890ff"
                      />
                    </div>
                    <div>
                      <span>复杂度</span>
                      <Progress
                        percent={Math.round(selectedExperience.complexity * 100)}
                        strokeColor="#faad14"
                      />
                    </div>
                  </div>
                </Card>
              </TabPane>

              <TabPane tab="评价与改进" key="feedback">
                <Card title="用户评分">
                  <Rate
                    disabled
                    value={selectedExperience.ratings.length > 0 ?
                      selectedExperience.ratings.reduce((a, b) => a + b, 0) /
                      selectedExperience.ratings.length : 0}
                  />
                  <span style={{ marginLeft: 16 }}>
                    {selectedExperience.ratings.length} 个评价
                  </span>
                </Card>

                <Card title="评论" style={{ marginTop: 16 }}>
                  {selectedExperience.comments.length > 0 ? (
                    selectedExperience.comments.map((comment, i) => (
                      <Comment
                        key={i}
                        author="用户"
                        content={comment}
                        datetime={new Date().toLocaleDateString()}
                      />
                    ))
                  ) : (
                    <Empty description="暂无评论" />
                  )}
                </Card>

                <Card title="改进建议" style={{ marginTop: 16 }}>
                  {selectedExperience.improvements.length > 0 ? (
                    <List
                      dataSource={selectedExperience.improvements}
                      renderItem={item => (
                        <List.Item>
                          <BulbOutlined style={{ marginRight: 8 }} />
                          {item}
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无改进建议" />
                  )}
                </Card>
              </TabPane>

              <TabPane tab="关联经验" key="related">
                {selectedExperience.related_experiences.length > 0 ? (
                  <List
                    dataSource={selectedExperience.related_experiences}
                    renderItem={id => (
                      <List.Item>
                        <Button type="link" icon={<ForkOutlined />}>
                          查看经验 {id}
                        </Button>
                      </List.Item>
                    )}
                  />
                ) : (
                  <Empty description="暂无关联经验" />
                )}
              </TabPane>
            </Tabs>
          </div>
        )}
      </Drawer>

      {/* 共享Modal */}
      <Modal
        title="共享经验"
        visible={shareModalVisible}
        onCancel={() => setShareModalVisible(false)}
        footer={null}
      >
        <Form
          layout="vertical"
          onFinish={(values) => {
            if (selectedExperience) {
              shareExperience(selectedExperience.experience_id, values.target_project);
            }
          }}
        >
          <Form.Item
            label="目标项目ID"
            name="target_project"
            rules={[{ required: true, message: '请输入目标项目ID' }]}
          >
            <Input placeholder="输入要共享到的项目ID" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">共享</Button>
              <Button onClick={() => setShareModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 反馈Modal */}
      <Modal
        title="提供反馈"
        visible={feedbackModalVisible}
        onCancel={() => setFeedbackModalVisible(false)}
        footer={null}
      >
        <Form
          layout="vertical"
          onFinish={(values) => {
            if (selectedExperience) {
              submitFeedback(selectedExperience.experience_id, values);
            }
          }}
        >
          <Form.Item label="这个经验对你有用吗？" name="success">
            <Select>
              <Option value={true}>是的，很有帮助</Option>
              <Option value={false}>没有解决我的问题</Option>
            </Select>
          </Form.Item>
          <Form.Item label="评分" name="rating">
            <Rate />
          </Form.Item>
          <Form.Item label="评论" name="comment">
            <TextArea rows={3} />
          </Form.Item>
          <Form.Item label="改进建议" name="improvement">
            <TextArea rows={3} placeholder="如何让这个经验更好？" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">提交</Button>
              <Button onClick={() => setFeedbackModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ExperienceHub;
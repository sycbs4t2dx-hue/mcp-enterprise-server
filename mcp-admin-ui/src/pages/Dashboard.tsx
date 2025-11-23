/**
 * Dashboard主页 - 4个Tab页面
 */

import { Tabs } from 'antd';
import {
  DashboardOutlined,
  DatabaseOutlined,
  SearchOutlined,
  FireOutlined
} from '@ant-design/icons';
import OverviewTab from '../components/OverviewTab';
import ConnectionPoolTab from '../components/ConnectionPoolTab';
import VectorSearchTab from '../components/VectorSearchTab';
import ErrorFirewallTab from '../components/ErrorFirewallTab';

interface DashboardProps {
  connected: boolean;
}

const Dashboard: React.FC<DashboardProps> = ({ connected }) => {
  const tabs = [
    {
      key: 'overview',
      label: (
        <span>
          <DashboardOutlined />
          系统概览
        </span>
      ),
      children: <OverviewTab connected={connected} />
    },
    {
      key: 'pool',
      label: (
        <span>
          <DatabaseOutlined />
          连接池监控
        </span>
      ),
      children: <ConnectionPoolTab connected={connected} />
    },
    {
      key: 'vector',
      label: (
        <span>
          <SearchOutlined />
          向量检索
        </span>
      ),
      children: <VectorSearchTab connected={connected} />
    },
    {
      key: 'firewall',
      label: (
        <span>
          <FireOutlined />
          错误防火墙
        </span>
      ),
      children: <ErrorFirewallTab connected={connected} />
    }
  ];

  return (
    <div>
      <Tabs
        defaultActiveKey="overview"
        size="large"
        items={tabs}
        style={{ background: 'white', padding: '16px', borderRadius: '8px' }}
        tabBarStyle={{
          borderBottom: '1px solid #f0f0f0',
        }}
        tabBarGutter={0}
      />
      <style>{`
        .ant-tabs-tab {
          min-width: 140px !important;
          justify-content: center !important;
          margin: 0 !important;
          padding: 12px 16px !important;
        }
        .ant-tabs-tab + .ant-tabs-tab {
          margin: 0 !important;
        }
        .ant-tabs-nav-list {
          width: 100% !important;
          display: flex !important;
        }
        .ant-tabs-nav-list .ant-tabs-tab {
          flex: 1 !important;
          margin: 0 !important;
        }
      `}</style>
    </div>
  );
};

export default Dashboard;

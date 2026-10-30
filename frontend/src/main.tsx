import { ConfigProvider } from 'antd';
import 'antd/dist/reset.css';
import zhCN from 'antd/locale/zh_CN';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './app/App';
import { appTheme } from './app/theme';
import './styles/index.css';

createRoot(document.getElementById('root')!).render(<StrictMode><ConfigProvider locale={zhCN} theme={appTheme}><App/></ConfigProvider></StrictMode>);

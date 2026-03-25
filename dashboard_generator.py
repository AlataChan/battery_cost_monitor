import os
import glob

class DashboardGenerator:
    def __init__(self):
        self.template_path = 'templates/dashboard_template.html'
        self.output_path = 'output/dashboard.html'
        self.reports_dir = 'output/reports'
        
    def generate_dashboard(self, cost_data: dict, chart_files: dict):
        """生成HTML仪表板"""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        
        # 读取最新报告
        latest_report = self._get_latest_report()
        
        # 读取HTML模板
        with open(self.template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 替换动态内容
        html_content = self._replace_dynamic_content(html_content, cost_data, chart_files, latest_report)
        
        # 保存仪表板
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"仪表板已生成: {self.output_path}")
        return self.output_path
    
    def _replace_dynamic_content(self, html_content: str, cost_data: dict, chart_files: dict, latest_report=None):
        """替换HTML模板中的动态内容"""
        # 替换时间戳
        html_content = html_content.replace('{{timestamp}}', cost_data['timestamp'])
        
        # 替换总成本信息
        html_content = html_content.replace('{{total_cost}}', f"{cost_data['total_cost']:.2f}")
        html_content = html_content.replace('{{cost_change}}', f"{cost_data['cost_change']:.2f}")
        html_content = html_content.replace('{{cost_change_pct}}', f"{cost_data['cost_change_pct']:.2f}")
        
        # 处理条件样式类
        cost_change = cost_data['cost_change']
        cost_change_pct = cost_data['cost_change_pct']
        
        # 替换成本变化的样式类
        cost_change_class = 'text-success' if cost_change < 0 else 'text-danger'
        cost_change_pct_class = 'text-success' if cost_change_pct < 0 else 'text-danger'
        
        # 替换成本变化符号
        cost_change_sign = '' if cost_change < 0 else '+'
        cost_change_pct_sign = '' if cost_change_pct < 0 else '+'
        
        # 替换模板中的条件表达式
        html_content = html_content.replace(
            "{{cost_change < 0 ? 'text-success' : 'text-danger'}}", 
            cost_change_class
        )
        html_content = html_content.replace(
            "{{cost_change_pct < 0 ? 'text-success' : 'text-danger'}}", 
            cost_change_pct_class
        )
        html_content = html_content.replace(
            "{{cost_change > 0 ? '+' : ''}}", 
            cost_change_sign
        )
        html_content = html_content.replace(
            "{{cost_change_pct > 0 ? '+' : ''}}", 
            cost_change_pct_sign
        )
        
        # 替换材料表格
        materials_html = self._generate_materials_table(cost_data['materials'])
        html_content = html_content.replace('{{materials_table}}', materials_html)
        
        # 替换图表路径 - 修复相对路径问题
        if 'cost_composition' in chart_files:
            # 保持完整路径 output/charts/xxx.png
            chart_path = chart_files['cost_composition']
            html_content = html_content.replace('{{cost_composition_chart}}', chart_path)
        else:
            html_content = html_content.replace('{{cost_composition_chart}}', '#')

        if 'cost_trend' in chart_files:
            # 保持完整路径 output/charts/xxx.png
            chart_path = chart_files['cost_trend']
            html_content = html_content.replace('{{cost_trend_chart}}', chart_path)
        else:
            html_content = html_content.replace('{{cost_trend_chart}}', '#')
        
        # 处理报告内容
        if latest_report:
            # 替换报告相关的内容
            html_content = self._replace_report_content(html_content, latest_report)
        else:
            # 如果没有报告，显示默认内容
            html_content = html_content.replace('{{latest_report}}', '<p class="text-muted">暂无最新报告</p>')
            html_content = html_content.replace('{{ai_insights_content}}', '<p class="text-muted">AI导师洞察暂不可用</p>')
            html_content = html_content.replace('{{predictions_content}}', '<p class="text-muted">价格预测数据暂不可用</p>')
        
        return html_content
    
    def _generate_materials_table(self, materials: dict) -> str:
        """生成材料表格HTML"""
        table_html = ""
        for material in materials.values():
            row_html = f"""
            <tr>
                <td>{material['name']}</td>
                <td>¥{material['baseline_price']:,.0f}</td>
                <td>¥{material['current_price']:,.0f}</td>
                <td class="{'text-danger' if material['cost_change'] >= 0 else 'text-success'}">
                    {'+' if material['cost_change'] >= 0 else ''}¥{material['cost_change']:.2f}
                </td>
                <td>{material['usage']}kg</td>
                <td>¥{material['baseline_cost']:.2f}</td>
                <td>¥{material['current_cost']:.2f}</td>
                <td class="{'text-danger' if material['cost_change'] >= 0 else 'text-success'}">
                    {'+' if material['cost_change'] >= 0 else ''}¥{material['cost_change']:.2f}
                </td>
            </tr>
            """
            table_html += row_html
        
        return table_html
    
    def _get_latest_report(self):
        """获取最新的报告文件并解析内容"""
        try:
            # 确保报告目录存在
            if not os.path.exists(self.reports_dir):
                return None
            
            # 获取最新的报告文件
            report_files = glob.glob(os.path.join(self.reports_dir, 'analysis_report_*.txt'))
            if not report_files:
                return None
            
            # 按修改时间排序，获取最新的报告
            latest_report_file = max(report_files, key=os.path.getmtime)
            
            # 解析报告内容
            return self._parse_report_content(latest_report_file)
            
        except Exception as e:
            print(f"获取最新报告失败: {e}")
            return None
    
    def _parse_report_content(self, report_path: str):
        """解析报告文件内容"""
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用明确的字典类型
            ai_insights: dict = {}
            predictions: dict = {}
            
            report_data = {
                'file_path': report_path,
                'file_name': os.path.basename(report_path),
                'content': content,
                'ai_insights': ai_insights,
                'predictions': predictions,
                'generation_time': '',
                'data_source': ''
            }
            
            lines = content.strip().split('\n')
            current_section = ''
            current_material = ''
            current_ai_advice = False
            
            for line in lines:
                # 保留原始行用于缩进判断
                original_line = line
                # 去空格的行用于内容处理
                line = line.strip()
                
                # 跳过空行
                if not line:
                    continue
                
                # 解析生成时间
                if line.startswith('生成时间:'):
                    report_data['generation_time'] = line.replace('生成时间:', '').strip()
                
                # 解析数据源
                elif line.startswith('数据源:'):
                    report_data['data_source'] = line.replace('数据源:', '').strip()
                
                # 解析AI导师洞察部分
                elif line.startswith('AI导师洞察:'):
                    current_section = 'ai_insights'
                elif line.startswith('价格预测摘要:'):
                    current_section = 'predictions'
                    current_ai_advice = False
                elif current_section == 'ai_insights':
                    if line.startswith('AI建议:'):
                        # 开始收集AI建议
                        ai_insights['AI建议'] = ''
                        current_ai_advice = True
                    elif current_ai_advice and line.strip() and not line.startswith('价格预测'):
                        # 收集AI建议内容
                        advice_content = line.strip()
                        if advice_content.startswith('1.') or advice_content.startswith('2.'):
                            advice_content = advice_content[2:].strip()
                        if ai_insights['AI建议']:
                            ai_insights['AI建议'] += ' ' + advice_content
                        else:
                            ai_insights['AI建议'] = advice_content
                    elif ':' in line and not line.startswith('AI建议:'):
                        current_ai_advice = False
                        try:
                            key, value = line.split(':', 1)
                            ai_insights[key.strip()] = value.strip()
                        except ValueError:
                            continue
                
                # 解析价格预测部分（使用原始行判断缩进）
                elif current_section == 'predictions':
                    # 检查是否为材料名（以2个空格开头并以:结尾，且不是4个空格）
                    if original_line.endswith(':') and original_line.startswith('  ') and not original_line.startswith('    '):
                        current_material = line.replace(':', '').strip()
                        if current_material not in predictions:
                            predictions[current_material] = {}
                    # 检查是否为材料属性（以4个空格开头并包含:）
                    elif current_material and ':' in line and original_line.startswith('    '):
                        try:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            predictions[current_material][key] = value
                        except ValueError:
                            continue
                    # 遇到生成图表，停止解析
                    elif line.startswith('生成图表'):
                        current_section = ''
                        current_material = ''
            
            return report_data
            
        except Exception as e:
            print(f"解析报告内容失败: {e}")
            return None
    
    def _replace_report_content(self, html_content: str, report_data: dict):
        """替换报告相关的内容"""
        # 替换最新报告基本信息
        report_info = f"""
        <div class="row">
            <div class="col-md-6">
                <strong><i class="fas fa-file-alt"></i> 报告文件:</strong><br>
                <span class="text-muted">{report_data.get('file_name', '未知文件')}</span>
            </div>
            <div class="col-md-6">
                <strong><i class="fas fa-clock"></i> 生成时间:</strong><br>
                <span class="text-muted">{report_data.get('generation_time', '未知时间')}</span>
            </div>
        </div>
        """
        html_content = html_content.replace('{{latest_report}}', report_info)
        
        # 替换AI导师洞察内容
        ai_insights_html = self._generate_ai_insights_html(report_data.get('ai_insights', {}))
        html_content = html_content.replace('{{ai_insights_content}}', ai_insights_html)
        
        # 替换价格预测内容
        predictions_html = self._generate_predictions_html(report_data.get('predictions', {}))
        html_content = html_content.replace('{{predictions_content}}', predictions_html)
        
        return html_content
    
    def _generate_ai_insights_html(self, ai_insights: dict):
        """生成AI导师洞察的HTML内容"""
        if not ai_insights:
            return '<p class="text-muted">暂无AI导师洞察数据</p>'
        
        html = '<div class="row">'
        
        # 成本趋势
        if '成本趋势' in ai_insights:
            trend = ai_insights['成本趋势']
            trend_class = 'success' if '稳定' in trend else 'warning' if '上升' in trend else 'info'
            html += f"""
            <div class="col-md-4 mb-3">
                <div class="card border-{trend_class}">
                    <div class="card-body text-center">
                        <i class="fas fa-chart-line fa-2x text-{trend_class} mb-2"></i>
                        <h6 class="card-title">成本趋势</h6>
                        <p class="card-text text-{trend_class}">{trend}</p>
                    </div>
                </div>
            </div>
            """
        
        # 变化幅度
        if '变化幅度' in ai_insights:
            change = ai_insights['变化幅度']
            change_class = 'success' if '-' in change else 'danger'
            html += f"""
            <div class="col-md-4 mb-3">
                <div class="card border-{change_class}">
                    <div class="card-body text-center">
                        <i class="fas fa-percentage fa-2x text-{change_class} mb-2"></i>
                        <h6 class="card-title">变化幅度</h6>
                        <p class="card-text text-{change_class}">{change}</p>
                    </div>
                </div>
            </div>
            """
        
        # 关注状态
        if '关注状态' in ai_insights:
            status = ai_insights['关注状态']
            status_class = 'success' if '正常' in status else 'warning'
            html += f"""
            <div class="col-md-4 mb-3">
                <div class="card border-{status_class}">
                    <div class="card-body text-center">
                        <i class="fas fa-shield-alt fa-2x text-{status_class} mb-2"></i>
                        <h6 class="card-title">关注状态</h6>
                        <p class="card-text text-{status_class}">{status}</p>
                    </div>
                </div>
            </div>
            """
        
        html += '</div>'
        
        # AI建议
        if 'AI建议' in ai_insights:
            suggestions = ai_insights['AI建议']
            html += f"""
            <div class="alert alert-info">
                <h6><i class="fas fa-lightbulb"></i> AI智能建议</h6>
                <p class="mb-0">{suggestions}</p>
            </div>
            """
        
        return html
    
    def _generate_predictions_html(self, predictions: dict):
        """生成价格预测的HTML内容"""
        if not predictions:
            return '<p class="text-muted">暂无价格预测数据</p>'
        
        html = '<div class="row">'
        
        for material, prediction in predictions.items():
            # 获取预测信息
            current_price = prediction.get('当前价格', '未知')
            predicted_price = prediction.get('预测价格', '未知')
            confidence = prediction.get('预测置信度', '未知')
            investment_advice = prediction.get('投资建议', '未知')
            score = prediction.get('综合评分', '未知')
            sentiment = prediction.get('AI情绪', '未知')
            risk_level = prediction.get('风险等级', '未知')
            
            # 根据投资建议设置颜色
            advice_class = 'success' if '买入' in investment_advice else 'warning' if '观望' in investment_advice else 'danger' if '卖出' in investment_advice else 'info'
            
            # 根据风险等级设置风险颜色
            risk_class = 'success' if '低' in risk_level else 'warning' if '中' in risk_level else 'danger'
            
            html += f"""
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header bg-{advice_class} text-white">
                        <h6 class="mb-0"><i class="fas fa-chart-line"></i> {material} 价格预测</h6>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6">
                                <small class="text-muted">当前价格</small>
                                <div class="fw-bold">{current_price}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">预测价格</small>
                                <div class="fw-bold text-{advice_class}">{predicted_price}</div>
                            </div>
                        </div>
                        <hr>
                        <div class="row">
                            <div class="col-6">
                                <small class="text-muted">置信度</small>
                                <div>{confidence}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">综合评分</small>
                                <div>{score}</div>
                            </div>
                        </div>
                        <hr>
                        <div class="row">
                            <div class="col-12">
                                <small class="text-muted">投资建议</small>
                                <div><span class="badge bg-{advice_class}">{investment_advice}</span></div>
                            </div>
                        </div>
                        <div class="row mt-2">
                            <div class="col-6">
                                <small class="text-muted">AI情绪</small>
                                <div>{sentiment}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">风险等级</small>
                                <div><span class="badge bg-{risk_class}">{risk_level}</span></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
        
        html += '</div>'
        return html
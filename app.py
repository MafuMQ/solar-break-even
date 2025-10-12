from flask import Flask, render_template, request, jsonify
import plotly.graph_objs as go
import plotly.utils
import json
import math

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        panel_cost = float(request.form['panel_cost'])
        panel_wattage = float(request.form['panel_wattage'])
        current_cost_per_kwh = float(request.form['current_cost'])
        daily_energy_kwh = float(request.form['daily_energy'])
        peak_power_w = float(request.form['peak_power'])
        # New: Get mode (annual/monthly)
        mode = request.form.get('mode', 'annual')

        # Validation
        if panel_wattage <= 0:
            raise ValueError("Panel wattage must be > 0.")
        if current_cost_per_kwh < 0:
            raise ValueError("Electricity cost cannot be negative.")
        if daily_energy_kwh < 0:
            raise ValueError("Daily energy cannot be negative.")
        if peak_power_w < 0:
            raise ValueError("Peak power cannot be negative.")
        if peak_power_w * 24 < daily_energy_kwh * 1000:
            # Warn: peak power must be able to supply daily energy in 24h
            # But we won't block — user might have storage or grid backup
            pass

        # Solar cost per watt
        solar_cost_per_watt = panel_cost / panel_wattage

        # REQUIRED: System must handle peak load
        required_capacity_w = peak_power_w

        # Total solar system cost
        total_solar_cost = required_capacity_w * solar_cost_per_watt

        # Annual energy consumption (kWh)
        annual_kwh = daily_energy_kwh * 365
        annual_grid_cost = annual_kwh * current_cost_per_kwh

        # Payback period
        if annual_grid_cost > 0:
            payback_period = total_solar_cost / annual_grid_cost
        else:
            payback_period = float('inf')

        # Graph data
        if mode == 'monthly':
            # Center break-even: show 2x break-even months, min 24, max 120
            if payback_period != float('inf'):
                break_even_month = int(math.ceil(payback_period * 12))
                max_periods = min(max(24, break_even_month * 2), 120)
            else:
                max_periods = 24
            periods = list(range(0, max_periods + 1))
            grid_cumulative = [annual_grid_cost / 12.0 * m for m in periods]
            solar_cumulative = [total_solar_cost if m == 0 else 0 for m in periods]
            grid_costs = [annual_grid_cost / 12.0 for _ in periods]
            solar_costs = [total_solar_cost if m == 0 else 0 for m in periods]
            cost_yaxis = 'Monthly Cost (R)'
            cum_xaxis = 'Months'
        else:
            max_periods = max(15, math.ceil(payback_period) + 5) if payback_period != float('inf') else 15
            periods = list(range(0, max_periods + 1))
            grid_cumulative = [annual_grid_cost * y for y in periods]
            solar_cumulative = [total_solar_cost for _ in periods]
            grid_costs = [annual_grid_cost for _ in periods]
            solar_costs = [total_solar_cost if y == 0 else 0 for y in periods]
            cost_yaxis = 'Annual Cost (R)'
            cum_xaxis = 'Years'

        # Cumulative cost graph
        fig_cumulative = go.Figure()
        fig_cumulative.add_trace(go.Scatter(x=periods, y=grid_cumulative, mode='lines+markers', name='Grid Electricity', line=dict(color='#1f77b4')))
        fig_cumulative.add_trace(go.Scatter(x=periods, y=solar_cumulative, mode='lines+markers', name='Solar System', line=dict(color='#2ca02c')))
        if payback_period != float('inf'):
            break_even_x = payback_period * 12 if mode == 'monthly' else payback_period
            if break_even_x <= max_periods:
                fig_cumulative.add_trace(go.Scatter(
                    x=[break_even_x], y=[total_solar_cost],
                    mode='markers', name=f'Break-Even ({payback_period:.1f} yrs)',
                    marker=dict(color='red', size=12, symbol='diamond')
                ))
        fig_cumulative.update_layout(
            title='Cumulative Cost: Solar vs Grid',
            xaxis_title=cum_xaxis,
            yaxis_title='Cumulative Cost (R)',
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)'),
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#333')
        )

        # Cost graph (annual/monthly)
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(x=periods, y=grid_costs, name='Grid Electricity', marker_color='#1f77b4'))
        fig_cost.add_trace(go.Bar(x=periods, y=solar_costs, name='Solar System', marker_color='#2ca02c'))
        fig_cost.update_layout(
            title=f'{cost_yaxis} Over Time',
            xaxis_title=cum_xaxis,
            yaxis_title=cost_yaxis,
            barmode='group',
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)'),
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#333')
        )

        graph_cumulative_json = json.dumps(fig_cumulative, cls=plotly.utils.PlotlyJSONEncoder)
        graph_cost_json = json.dumps(fig_cost, cls=plotly.utils.PlotlyJSONEncoder)

        return jsonify({
            'success': True,
            'required_capacity_w': round(required_capacity_w, 1),
            'total_solar_cost': round(total_solar_cost, 2),
            'annual_savings': round(annual_grid_cost, 2),
            'payback_period': round(payback_period, 2) if payback_period != float('inf') else 'Never',
            'graph_cumulative': graph_cumulative_json,
            'graph_cost': graph_cost_json
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
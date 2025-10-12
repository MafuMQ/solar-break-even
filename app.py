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
        daily_energy_wh = float(request.form['daily_energy'])
        peak_power_w = float(request.form['peak_power'])

        # Validation
        if panel_wattage <= 0:
            raise ValueError("Panel wattage must be > 0.")
        if current_cost_per_kwh < 0:
            raise ValueError("Electricity cost cannot be negative.")
        if daily_energy_wh < 0:
            raise ValueError("Daily energy cannot be negative.")
        if peak_power_w < 0:
            raise ValueError("Peak power cannot be negative.")
        if peak_power_w * 24 < daily_energy_wh:
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
        annual_kwh = (daily_energy_wh / 1000.0) * 365
        annual_grid_cost = annual_kwh * current_cost_per_kwh

        # Payback period
        if annual_grid_cost > 0:
            payback_period = total_solar_cost / annual_grid_cost
        else:
            payback_period = float('inf')

        # Graph data
        max_years = max(15, math.ceil(payback_period) + 5) if payback_period != float('inf') else 15
        years = list(range(0, max_years + 1))
        grid_costs = [annual_grid_cost * y for y in years]
        solar_costs = [total_solar_cost for _ in years]

        # Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=years, y=grid_costs, mode='lines+markers', name='Grid Electricity', line=dict(color='#1f77b4')))
        fig.add_trace(go.Scatter(x=years, y=solar_costs, mode='lines+markers', name='Solar System', line=dict(color='#2ca02c')))

        if payback_period != float('inf') and payback_period <= max_years:
            fig.add_trace(go.Scatter(
                x=[payback_period], y=[total_solar_cost],
                mode='markers', name=f'Break-Even ({payback_period:.1f} yrs)',
                marker=dict(color='red', size=12, symbol='diamond')
            ))

        fig.update_layout(
            title='Cumulative Cost: Solar vs Grid',
            xaxis_title='Years',
            yaxis_title='Cumulative Cost ($)',
            legend=dict(x=0.02, y=0.98, bgcolor='rgba(255,255,255,0.8)'),
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#333')
        )

        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        return jsonify({
            'success': True,
            'required_capacity_w': round(required_capacity_w, 1),
            'total_solar_cost': round(total_solar_cost, 2),
            'annual_savings': round(annual_grid_cost, 2),
            'payback_period': round(payback_period, 2) if payback_period != float('inf') else 'Never',
            'graph': graph_json
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
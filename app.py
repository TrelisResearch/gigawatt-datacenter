import gradio as gr
import plotly.graph_objects as go
from solar import analyze_solar_system
import config

def solar_analysis(city, country, demand_gw, 
                   solar_cost, wind_cost, battery_cost, 
                   solar_efficiency, solar_density,
                   ng_price, ocgt_efficiency, ocgt_capex, ocgt_opex,
                   ccgt_efficiency, ccgt_capex, ccgt_opex,
                   project_lifetime, solar_battery_hours, wind_battery_hours,
                   cutoff_day, hybrid_threshold):
    
    # Update config values
    config.SOLAR_COST_PER_KW = solar_cost
    config.WIND_COST_PER_KW = wind_cost
    config.BATTERY_COST_PER_KWH = battery_cost
    config.SOLAR_PANEL_EFFICIENCY = solar_efficiency
    config.SOLAR_PANEL_DENSITY = solar_density
    config.NG_PRICE_PER_MMBTU = ng_price
    config.NG_PRICE_PER_KWH = ng_price / 293.07
    config.OCGT_EFFICIENCY = ocgt_efficiency
    config.OCGT_CAPEX_PER_KW = ocgt_capex
    config.OCGT_OPEX_PER_KWH = ocgt_opex
    config.CCGT_EFFICIENCY = ccgt_efficiency
    config.CCGT_CAPEX_PER_KW = ccgt_capex
    config.CCGT_OPEX_PER_KWH = ccgt_opex
    config.PROJECT_LIFETIME = project_lifetime
    config.SOLAR_BATTERY_STORAGE_HOURS = solar_battery_hours
    config.WIND_BATTERY_STORAGE_HOURS = wind_battery_hours
    config.CUTOFF_DAY = cutoff_day
    config.HYBRID_LCOE_THRESHOLD = hybrid_threshold

    demand_kw = demand_gw * 1e6
    daily_usage = demand_kw * 24
    results = analyze_solar_system(city, country, demand_kw, daily_usage)
    
    output_text = f"""
    Solar + Gas System Results:
    LCOE: ${results['lcoe']:.4f}/kWh
    Solar Fraction: {results['solar_fraction']:.2%}
    Gas Fraction: {results['gas_fraction']:.2%}
    Solar Capacity Factor: {results['capacity_factor']:.2%}
    Solar Area: {results['solar_area_km2']:.2f} km² ({results['solar_area_percentage']:.2f}% of Ireland)
    Solar Capacity: {results['solar_capacity_gw']:.2f} GW
    Gas Capacity: {results['gas_capacity_gw']:.2f} GW
    Capex per kW: ${results['capex_per_kw']:.2f} million/kW
    Total Capex: ${results['total_capex']:.2f} million
    """
    
    # Create energy output plot
    energy_data = results['energy_output_data']
    energy_fig = go.Figure()
    energy_fig.add_trace(go.Bar(x=list(range(len(energy_data['solar_output']))), 
                                y=energy_data['solar_output'], 
                                name='Solar Output', 
                                marker_color='yellow'))
    energy_fig.add_trace(go.Bar(x=list(range(len(energy_data['gas_output']))), 
                                y=energy_data['gas_output'], 
                                name='Generator Output', 
                                marker_color='gray'))
    energy_fig.update_layout(title=f'Daily Energy Output in {city}: Solar vs Gas',
                             xaxis_title='Days (sorted by solar output)',
                             yaxis_title='Energy Output (kWh)',
                             barmode='stack')

    # Create capex breakdown plot
    capex_data = results['capex_breakdown_data']
    capex_fig = go.Figure(data=[go.Pie(labels=capex_data['components'], 
                                       values=capex_data['values'], 
                                       hole=.3)])
    capex_fig.update_layout(title=f'Capex Breakdown for Solar + Gas System in {city} ($ million)')

    return output_text, energy_fig, capex_fig

with gr.Blocks() as iface:
    gr.Markdown("# Solar + Gas Energy System Analysis")
    gr.Markdown("Analyze a solar energy system with gas backup for a given location and demand.")
    
    with gr.Row():
        city = gr.Textbox(label="City", value="Waterford")
        country = gr.Textbox(label="Country", value="Ireland")
        demand_gw = gr.Slider(minimum=0.1, maximum=10, value=1, label="Demand (GW)")
    
    submit_button = gr.Button("Submit")

    with gr.Tabs():
        with gr.TabItem("Solar Analysis Results"):
            results = gr.Textbox(label="Results")
            energy_output = gr.Plot(label="Energy Output")
            capex_breakdown = gr.Plot(label="Capex Breakdown")
        
        with gr.TabItem("Advanced Settings"):
            with gr.Column():
                gr.Markdown("### Cost Parameters")
                wind_cost = gr.Slider(minimum=500, maximum=2000, value=config.WIND_COST_PER_KW, label="Wind Cost ($/kW)", info="Cost per kW of wind installation")
                battery_cost = gr.Slider(minimum=100, maximum=500, value=config.BATTERY_COST_PER_KWH, label="Battery Cost ($/kWh)", info="Cost per kWh of battery storage")

                gr.Markdown("### Solar Parameters")
                solar_cost = gr.Slider(minimum=100, maximum=1000, value=config.SOLAR_COST_PER_KW, label="Solar Cost ($/kW)", info="Cost per kW of solar installation")
                solar_efficiency = gr.Slider(minimum=0.1, maximum=0.3, value=config.SOLAR_PANEL_EFFICIENCY, label="Solar Panel Efficiency", info="Efficiency of solar panels")
                solar_density = gr.Slider(minimum=0.2, maximum=0.6, value=config.SOLAR_PANEL_DENSITY, label="Solar Panel Density", info="m² of panel area per m² of land")
                solar_battery_hours = gr.Slider(minimum=6, maximum=48, value=config.SOLAR_BATTERY_STORAGE_HOURS, label="Solar Battery Storage (hours)", info="Hours of battery storage for solar system")
                
                gr.Markdown("### Gas Parameters")
                ng_price = gr.Slider(minimum=5, maximum=50, value=config.NG_PRICE_PER_MMBTU, label="Natural Gas Price (€/MMBtu)", info="Price of natural gas")
                ocgt_efficiency = gr.Slider(minimum=0.2, maximum=0.5, value=config.OCGT_EFFICIENCY, label="OCGT Efficiency", info="Efficiency of open cycle gas turbine")
                ocgt_capex = gr.Slider(minimum=400, maximum=1200, value=config.OCGT_CAPEX_PER_KW, label="OCGT CAPEX ($/kW)", info="Capital expenditure for OCGT")
                ocgt_opex = gr.Slider(minimum=0.01, maximum=0.05, value=config.OCGT_OPEX_PER_KWH, label="OCGT OPEX (€/kWh)", info="Operating expenditure for OCGT")
                ccgt_efficiency = gr.Slider(minimum=0.4, maximum=0.7, value=config.CCGT_EFFICIENCY, label="CCGT Efficiency", info="Efficiency of combined cycle gas turbine")
                ccgt_capex = gr.Slider(minimum=800, maximum=1600, value=config.CCGT_CAPEX_PER_KW, label="CCGT CAPEX ($/kW)", info="Capital expenditure for CCGT")
                ccgt_opex = gr.Slider(minimum=0.005, maximum=0.03, value=config.CCGT_OPEX_PER_KWH, label="CCGT OPEX (€/kWh)", info="Operating expenditure for CCGT")
                
                gr.Markdown("### System Parameters")
                project_lifetime = gr.Slider(minimum=10, maximum=30, value=config.PROJECT_LIFETIME, label="Project Lifetime (years)", info="Expected lifetime of the project")
                wind_battery_hours = gr.Slider(minimum=6, maximum=48, value=config.WIND_BATTERY_STORAGE_HOURS, label="Wind Battery Storage (hours)", info="Hours of battery storage for wind system")
                cutoff_day = gr.Slider(minimum=10, maximum=100, value=config.CUTOFF_DAY, label="Cutoff Day", info="Days system should handle without gas")
                hybrid_threshold = gr.Slider(minimum=0.05, maximum=0.3, value=config.HYBRID_LCOE_THRESHOLD, label="Hybrid LCOE Threshold", info="If hybrid solar + wind is not this fraction cheaper than wind or solar alone, defaults to the cheaper of wind OR solar.")

    submit_button.click(
        fn=solar_analysis,
        inputs=[
            city, country, demand_gw,
            solar_cost, wind_cost, battery_cost,
            solar_efficiency, solar_density,
            ng_price, ocgt_efficiency, ocgt_capex, ocgt_opex,
            ccgt_efficiency, ccgt_capex, ccgt_opex,
            project_lifetime, solar_battery_hours, wind_battery_hours,
            cutoff_day, hybrid_threshold
        ],
        outputs=[results, energy_output, capex_breakdown]
    )

iface.launch()
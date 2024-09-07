import gradio as gr
import plotly.graph_objects as go
from solar import analyze_solar_system
from wind import analyze_wind_energy
import config

def analyze_energy_systems(city, country, demand_gw, 
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

    # Solar analysis
    solar_results = analyze_solar_system(city, country, demand_kw, daily_usage)
    
    solar_output_text = f"""
    Solar + Gas System Results:
    LCOE: ${solar_results['lcoe']:.4f}/kWh
    Solar Fraction: {solar_results['solar_fraction']:.2%}
    Gas Fraction: {solar_results['gas_fraction']:.2%}
    Solar Capacity Factor: {solar_results['capacity_factor']:.2%}
    Solar Area: {solar_results['solar_area_km2']:.2f} km² ({solar_results['solar_area_percentage']:.2f}% of Ireland)
    Solar Capacity: {solar_results['solar_capacity_gw']:.2f} GW
    Gas Capacity: {solar_results['gas_capacity_gw']:.2f} GW
    Capex per kW: ${solar_results['capex_per_kw']} $/kW
    Total Capex: ${solar_results['total_capex']:.2f} million
    """
    
    solar_energy_fig = go.Figure()
    solar_energy_fig.add_trace(go.Bar(x=list(range(len(solar_results['energy_output_data']['solar_output']))), 
                                      y=solar_results['energy_output_data']['solar_output'], 
                                      name='Solar Output', 
                                      marker_color='yellow'))
    solar_energy_fig.add_trace(go.Bar(x=list(range(len(solar_results['energy_output_data']['gas_output']))), 
                                      y=solar_results['energy_output_data']['gas_output'], 
                                      name='Generator Output', 
                                      marker_color='gray'))
    solar_energy_fig.update_layout(title=f'Daily Energy Output in {city}: Solar vs Gas',
                                   xaxis_title='Days (sorted by solar output)',
                                   yaxis_title='Energy Output (kWh)',
                                   barmode='stack')

    solar_capex_fig = go.Figure(data=[go.Pie(labels=solar_results['capex_breakdown_data']['components'], 
                                             values=solar_results['capex_breakdown_data']['values'], 
                                             hole=.3)])
    solar_capex_fig.update_layout(title=f'Capex Breakdown for Solar + Gas System in {city} ($ million)')

    # Wind analysis
    wind_results = analyze_wind_energy(city, country, daily_usage, demand_kw, cutoff_day)
    
    wind_output_text = f"""
    Wind + Gas System Results:
    LCOE: ${wind_results['lcoe']:.4f}/kWh
    Wind Fraction: {wind_results['wind_fraction']:.2%}
    Gas Fraction: {wind_results['generator_fraction']:.2%}
    Wind Capacity Factor: {wind_results['capacity_factor']:.2%}
    Wind Capacity: {wind_results['wind_capacity_gw']:.2f} GW
    Gas Capacity: {wind_results['generator_capacity_gw']:.2f} GW
    Capex per kW: ${wind_results['capex_per_kw']} $/kW
    Total Capex: ${wind_results['total_capex']:.2f} million
    """
    
    wind_energy_fig = go.Figure()
    wind_energy_fig.add_trace(go.Bar(x=list(range(len(wind_results['energy_output_data']['wind_output']))), 
                                     y=wind_results['energy_output_data']['wind_output'], 
                                     name='Wind Output', 
                                     marker_color='blue'))
    wind_energy_fig.add_trace(go.Bar(x=list(range(len(wind_results['energy_output_data']['generator_output']))), 
                                     y=wind_results['energy_output_data']['generator_output'], 
                                     name='Generator Output', 
                                     marker_color='gray'))
    wind_energy_fig.update_layout(title=f'Daily Energy Output in {city}: Wind vs Gas',
                                  xaxis_title='Days (sorted by wind output)',
                                  yaxis_title='Energy Output (kWh)',
                                  barmode='stack')

    wind_capex_fig = go.Figure(data=[go.Pie(labels=wind_results['capex_breakdown_data']['components'], 
                                            values=wind_results['capex_breakdown_data']['values'], 
                                            hole=.3)])
    wind_capex_fig.update_layout(title=f'Capex Breakdown for Wind + Gas System in {city} ($ million)')

    return (solar_output_text, solar_energy_fig, solar_capex_fig,
            wind_output_text, wind_energy_fig, wind_capex_fig)

with gr.Blocks() as iface:
    gr.Markdown("# Solar/Wind + Gas Energy System Analysis")
    gr.Markdown("Analyze a solar or wind energy system with gas backup for a given location and demand.")
    
    with gr.Row():
        city = gr.Textbox(label="City", value="Waterford")
        country = gr.Textbox(label="Country", value="Ireland")
        demand_gw = gr.Slider(minimum=0.1, maximum=10, value=1, label="Demand (GW)")
    
    submit_button = gr.Button("Submit")

    with gr.Tabs():
        with gr.TabItem("Solar Analysis Results"):
            solar_results = gr.Textbox(label="Results")
            solar_energy_output = gr.Plot(label="Energy Output")
            solar_capex_breakdown = gr.Plot(label="Capex Breakdown")
        
        with gr.TabItem("Wind Analysis Results"):
            wind_results = gr.Textbox(label="Results")
            wind_energy_output = gr.Plot(label="Energy Output")
            wind_capex_breakdown = gr.Plot(label="Capex Breakdown")
        
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
        fn=analyze_energy_systems,
        inputs=[
            city, country, demand_gw,
            solar_cost, wind_cost, battery_cost,
            solar_efficiency, solar_density,
            ng_price, ocgt_efficiency, ocgt_capex, ocgt_opex,
            ccgt_efficiency, ccgt_capex, ccgt_opex,
            project_lifetime, solar_battery_hours, wind_battery_hours,
            cutoff_day, hybrid_threshold
        ],
        outputs=[
            solar_results, solar_energy_output, solar_capex_breakdown,
            wind_results, wind_energy_output, wind_capex_breakdown
        ]
    )

iface.launch()
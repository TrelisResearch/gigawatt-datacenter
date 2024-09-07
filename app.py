import gradio as gr
import plotly.graph_objects as go
from solar import analyze_solar_system
from wind import analyze_wind_energy
from ccgt import analyze_ccgt
from solar_wind import analyze_hybrid_system
import config
from geopy.geocoders import Nominatim

def get_coordinates(location):
    geolocator = Nominatim(user_agent="SolarScript/1.0")
    try:
        location_data = geolocator.geocode(location, exactly_one=True, timeout=10)
        if location_data:
            return location_data.latitude, location_data.longitude
        else:
            return None
    except Exception as e:
        print(f"Error in geocoding: {e}")
        return None

def validate_coordinates(lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
        else:
            return None
    except ValueError:
        return None

def analyze_energy_systems(lat, lon, demand_gw, 
                           solar_cost, wind_cost, battery_cost, 
                           solar_efficiency, solar_density,
                           ng_price, ocgt_efficiency, ocgt_capex, ocgt_opex,
                           ccgt_efficiency, ccgt_capex, ccgt_opex,
                           project_lifetime, solar_battery_hours, wind_battery_hours,
                           cutoff_day, hybrid_threshold,
                           equity_premium, debt_premium, debt_ratio, tax_rate):
    
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
    config.EQUITY_PREMIUM = equity_premium / 100
    config.DEBT_PREMIUM = debt_premium / 100
    config.DEBT_RATIO = debt_ratio / 100
    config.EQUITY_RATIO = 1 - (debt_ratio / 100)
    config.TAX_RATE = tax_rate / 100

    demand_kw = demand_gw * 1e6
    daily_usage = demand_kw * 24

    # Solar analysis
    solar_results = analyze_solar_system(lat, lon, demand_kw, daily_usage)
    
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
    
    # Update plot styling
    plot_layout = dict(
        font=dict(size=14),
        title_font_size=18,
        legend=dict(font=dict(size=12)),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    # Color palette
    colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99CC', '#99CCFF']

    # Solar energy output plot
    solar_energy_fig = go.Figure()
    solar_energy_fig.add_trace(go.Bar(x=list(range(len(solar_results['energy_output_data']['solar_output']))), 
                                      y=solar_results['energy_output_data']['solar_output'], 
                                      name='Solar Output', 
                                      marker_color=colors[0]))
    solar_energy_fig.add_trace(go.Bar(x=list(range(len(solar_results['energy_output_data']['gas_output']))), 
                                      y=solar_results['energy_output_data']['gas_output'], 
                                      name='Gas Output', 
                                      marker_color=colors[1]))
    solar_energy_fig.update_layout(
        title=f'Daily Energy Output in {lat}, {lon}: Solar vs Gas',
        xaxis_title='Days (sorted by solar output)',
        yaxis_title='Energy Output (kWh)',
        barmode='stack',
        **plot_layout
    )

    # Solar capex breakdown plot
    solar_capex_fig = go.Figure(go.Bar(
        y=['Total'],
        x=[solar_results['capex_per_kw']],
        orientation='h',
        marker_color=colors[0],
        name='Solar'
    ))
    solar_capex_fig.add_trace(go.Bar(
        y=['Total'],
        x=[solar_results['capex_breakdown_data']['values'][1]],  # Assuming battery is the second item
        orientation='h',
        marker_color=colors[1],
        name='Battery'
    ))
    solar_capex_fig.add_trace(go.Bar(
        y=['Total'],
        x=[solar_results['capex_breakdown_data']['values'][2]],  # Assuming gas is the third item
        orientation='h',
        marker_color=colors[2],
        name='Gas'
    ))
    solar_capex_fig.update_layout(
        title=f'Capex Breakdown for Solar + Gas System ($/kW)',
        xaxis_title='Capex ($/kW)',
        barmode='stack',
        **plot_layout
    )

    # Wind analysis
    wind_results = analyze_wind_energy(lat, lon, daily_usage, demand_kw, cutoff_day)
    
    wind_output_text = f"""
    Wind + Gas System Results:
    LCOE: ${wind_results['lcoe']:.4f}/kWh
    Wind Fraction: {wind_results['wind_fraction']:.2%}
    Gas Fraction: {wind_results['gas_fraction']:.2%}
    Wind Capacity Factor: {wind_results['capacity_factor']:.2%}
    Wind Capacity: {wind_results['wind_capacity_gw']:.2f} GW
    Gas Capacity: {wind_results['gas_capacity_gw']:.2f} GW
    Capex per kW: ${wind_results['capex_per_kw']} $/kW
    Total Capex: ${wind_results['total_capex']:.2f} million
    """
    
    # Wind energy output plot
    wind_energy_fig = go.Figure()
    wind_energy_fig.add_trace(go.Bar(x=list(range(len(wind_results['energy_output_data']['wind_output']))), 
                                     y=wind_results['energy_output_data']['wind_output'], 
                                     name='Wind Output', 
                                     marker_color=colors[2]))
    wind_energy_fig.add_trace(go.Bar(x=list(range(len(wind_results['energy_output_data']['gas_output']))), 
                                     y=wind_results['energy_output_data']['gas_output'], 
                                     name='Gas Output', 
                                     marker_color=colors[1]))
    wind_energy_fig.update_layout(
        title=f'Daily Energy Output in {lat}, {lon}: Wind vs Gas',
        xaxis_title='Days (sorted by wind output)',
        yaxis_title='Energy Output (kWh)',
        barmode='stack',
        **plot_layout
    )

    # Wind capex breakdown plot
    wind_capex_fig = go.Figure(go.Bar(
        y=['Total'],
        x=[wind_results['capex_breakdown_data']['values'][0]],
        orientation='h',
        marker_color=colors[2],
        name='Wind'
    ))
    wind_capex_fig.add_trace(go.Bar(
        y=['Total'],
        x=[wind_results['capex_breakdown_data']['values'][1]],  # Assuming battery is the second item
        orientation='h',
        marker_color=colors[1],
        name='Battery'
    ))
    wind_capex_fig.add_trace(go.Bar(
        y=['Total'],
        x=[wind_results['capex_breakdown_data']['values'][2]],  # Assuming gas is the third item
        orientation='h',
        marker_color=colors[3],
        name='Gas'
    ))
    wind_capex_fig.update_layout(
        title=f'Capex Breakdown for Wind + Gas System ($/kW)',
        xaxis_title='Capex ($/kW)',
        barmode='stack',
        **plot_layout
    )

    # CCGT analysis
    ccgt_results = analyze_ccgt(daily_usage, demand_kw)
    
    ccgt_output_text = f"""
    CCGT System Results:
    LCOE: ${ccgt_results['lcoe']:.4f}/kWh
    Capacity: {ccgt_results['capacity_gw']:.2f} GW
    Capex per kW: ${ccgt_results['capex_per_kw']:.2f}/kW
    Total Capex: ${ccgt_results['total_capex']:,.0f}
    Annual Energy Used: {ccgt_results['annual_energy_used']:,.0f} kWh
    WACC: {ccgt_results['wacc']:.4%}
    """
    
    # CCGT cost breakdown plot
    ccgt_cost_fig = go.Figure(go.Bar(
        x=ccgt_results['cost_breakdown']['values'],
        y=ccgt_results['cost_breakdown']['components'],
        orientation='h',
        marker_color=colors
    ))
    ccgt_cost_fig.update_layout(
        title='Annual Cost Breakdown for CCGT',
        xaxis_title='Cost ($)',
        **plot_layout
    )

    # Hybrid system analysis
    hybrid_results = analyze_hybrid_system(lat, lon, demand_kw, daily_usage, cutoff_day)
    
    hybrid_output_text = f"""
    Wind + Gas System Results:
    LCOE: ${hybrid_results['lcoe']:.4f}/kWh
    Solar Fraction: {hybrid_results['solar_fraction']:.2%}
    Wind Fraction: {hybrid_results['wind_fraction']:.2%}
    Gas Fraction: {hybrid_results['gas_fraction']:.2%}
    Solar Capacity Factor: {hybrid_results['solar_capacity_factor']:.2%}
    Wind Capacity Factor: {hybrid_results['wind_capacity_factor']:.2%}
    Solar Capacity: {hybrid_results['solar_capacity_gw']:.2f} GW
    Wind Capacity: {hybrid_results['wind_capacity_gw']:.2f} GW
    Gas Capacity: {hybrid_results['gas_capacity_gw']:.2f} GW
    Battery Capacity: {hybrid_results['battery_capacity_gwh']:.2f} GWh
    Capex per kW: ${hybrid_results['capex_per_kw']:.2f}/kW
    Total Capex: ${hybrid_results['total_capex']:.2f} million
    """
    
    # Hybrid energy output plot
    hybrid_energy_fig = go.Figure()
    hybrid_energy_fig.add_trace(go.Bar(x=list(range(len(hybrid_results['energy_output_data']['solar_output']))), 
                                       y=hybrid_results['energy_output_data']['solar_output'], 
                                       name='Solar Output', 
                                       marker_color=colors[0]))
    hybrid_energy_fig.add_trace(go.Bar(x=list(range(len(hybrid_results['energy_output_data']['wind_output']))), 
                                       y=hybrid_results['energy_output_data']['wind_output'], 
                                       name='Wind Output', 
                                       marker_color=colors[2]))
    hybrid_energy_fig.add_trace(go.Bar(x=list(range(len(hybrid_results['energy_output_data']['gas_output']))), 
                                       y=hybrid_results['energy_output_data']['gas_output'], 
                                       name='Gas Output', 
                                       marker_color=colors[1]))
    hybrid_energy_fig.update_layout(
        title=f'Daily Energy Output in {lat}, {lon}: Solar, Wind, and Gas',
        xaxis_title='Days (sorted by combined output)',
        yaxis_title='Energy Output (kWh)',
        barmode='stack',
        **plot_layout
    )

    # Hybrid capex breakdown plot
    hybrid_capex_fig = go.Figure(go.Bar(
        y=['Total'],
        x=[hybrid_results['capex_breakdown_data']['values'][0]],
        orientation='h',
        marker_color=colors[0],
        name='Solar'
    ))
    hybrid_capex_fig.add_trace(go.Bar(
        y=['Total'],
        x=[hybrid_results['capex_breakdown_data']['values'][1]],
        orientation='h',
        marker_color=colors[2],
        name='Wind'
    ))
    hybrid_capex_fig.add_trace(go.Bar(
        y=['Total'],
        x=[hybrid_results['capex_breakdown_data']['values'][2]],
        orientation='h',
        marker_color=colors[1],
        name='Battery'
    ))
    hybrid_capex_fig.add_trace(go.Bar(
        y=['Total'],
        x=[hybrid_results['capex_breakdown_data']['values'][3]],
        orientation='h',
        marker_color=colors[3],
        name='Gas'
    ))
    hybrid_capex_fig.update_layout(
        title=f'Capex Breakdown for {hybrid_results["system_type"]} System ($/kW)',
        xaxis_title='Capex ($/kW)',
        barmode='stack',
        **plot_layout
    )

    return (solar_output_text, solar_energy_fig, solar_capex_fig,
            wind_output_text, wind_energy_fig, wind_capex_fig,
            ccgt_output_text, ccgt_cost_fig,
            hybrid_output_text, hybrid_energy_fig, hybrid_capex_fig)

def analyze_energy_systems_wrapper(input_type, location, lat, lon, demand_gw, *args):
    try:
        if input_type == "Location":
            coordinates = get_coordinates(location)
            if coordinates:
                lat, lon = coordinates
                print(f"Coordinates found for location: {lat}, {lon}")
            else:
                return "Location not found. Please try a more specific location or use latitude and longitude.", None, None, None, None, None, None, None, None, None, None
        elif input_type == "Coordinates":
            coordinates = validate_coordinates(lat, lon)
            if coordinates:
                lat, lon = coordinates
                print(f"Using provided coordinates: {lat}, {lon}")
            else:
                return "Invalid latitude or longitude. Please enter valid coordinates.", None, None, None, None, None, None, None, None, None, None
        else:
            return "Please select either location or coordinates input method.", None, None, None, None, None, None, None, None, None, None
        
        return analyze_energy_systems(lat, lon, demand_gw, *args)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        return error_message, None, None, None, None, None, None, None, None, None, None

def update_visibility(choice):
    return (
        gr.Column(visible=(choice == "Location")),
        gr.Column(visible=(choice == "Coordinates"))
    )

with gr.Blocks() as iface:
    gr.Markdown("# Solar/Wind + Gas Energy System Analysis")
    gr.Markdown("Analyze a solar or wind energy system with gas backup for a given location and demand.")
    
    input_type = gr.Radio(["Location", "Coordinates"], label="Input Method", value="Location")
    
    with gr.Column(visible=True) as location_column:
        location = gr.Textbox(
            label="Location", 
            value="Waterford, Ireland", 
            info="Enter a specific location (e.g., 'New York, USA' or 'Berlin, Germany')"
        )
    
    with gr.Column(visible=False) as coordinates_column:
        with gr.Row():
            latitude = gr.Textbox(
                label="Latitude",
                placeholder="e.g., 52.2593",
                info="Enter latitude (between -90 and 90)"
            )
            longitude = gr.Textbox(
                label="Longitude",
                placeholder="e.g., -7.1101",
                info="Enter longitude (between -180 and 180)"
            )

    with gr.Row():
        demand_gw = gr.Slider(minimum=0.1, maximum=10, value=1, label="Demand (GW)")
    
    submit_button = gr.Button("Submit")

    with gr.Tabs() as tabs:
        with gr.TabItem("Solar Analysis Results", id="solar_tab"):
            solar_results = gr.Textbox(label="Results")
            solar_energy_output = gr.Plot(label="Energy Output")
            solar_capex_breakdown = gr.Plot(label="Capex Breakdown")
        
        with gr.TabItem("Wind Analysis Results", id="wind_tab"):
            wind_results = gr.Textbox(label="Results")
            wind_energy_output = gr.Plot(label="Energy Output")
            wind_capex_breakdown = gr.Plot(label="Capex Breakdown")
        
        with gr.TabItem("Hybrid System Analysis Results", id="hybrid_tab"):
            hybrid_results = gr.Textbox(label="Results")
            hybrid_energy_output = gr.Plot(label="Energy Output")
            hybrid_capex_breakdown = gr.Plot(label="Capex Breakdown")

        with gr.TabItem("CCGT Analysis Results", id="ccgt_tab"):
            ccgt_results = gr.Textbox(label="Results")
            ccgt_cost_breakdown = gr.Plot(label="Annual Cost Breakdown")

        with gr.TabItem("Advanced Settings", id="advanced_tab"):
            with gr.Column():
                gr.Markdown("### Cost Parameters")
                solar_cost = gr.Slider(minimum=100, maximum=1000, value=config.SOLAR_COST_PER_KW, label="Solar Cost ($/kW)", info="Cost per kW of solar installation")
                wind_cost = gr.Slider(minimum=500, maximum=2000, value=config.WIND_COST_PER_KW, label="Wind Cost ($/kW)", info="Cost per kW of wind installation")
                battery_cost = gr.Slider(minimum=100, maximum=500, value=config.BATTERY_COST_PER_KWH, label="Battery Cost ($/kWh)", info="Cost per kWh of battery storage")

                gr.Markdown("### Solar Parameters")
                solar_efficiency = gr.Slider(minimum=0.1, maximum=0.3, value=config.SOLAR_PANEL_EFFICIENCY, label="Solar Panel Efficiency", info="Efficiency of solar panels")
                solar_density = gr.Slider(minimum=0.2, maximum=0.6, value=config.SOLAR_PANEL_DENSITY, label="Solar Panel Density", info="m² of panel area per m² of land")
                solar_battery_hours = gr.Slider(minimum=6, maximum=48, value=config.SOLAR_BATTERY_STORAGE_HOURS, label="Solar Battery Storage (hours)", info="Hours of battery storage for solar system")
                
                gr.Markdown("### Gas Parameters")
                ng_price = gr.Slider(minimum=5, maximum=50, value=config.NG_PRICE_PER_MMBTU, label="Natural Gas Price ($/MMBtu)", info="Price of natural gas")
                ocgt_efficiency = gr.Slider(minimum=0.2, maximum=0.5, value=config.OCGT_EFFICIENCY, label="OCGT Efficiency", info="Efficiency of open cycle gas turbine")
                ocgt_capex = gr.Slider(minimum=400, maximum=1200, value=config.OCGT_CAPEX_PER_KW, label="OCGT CAPEX ($/kW)", info="Capital expenditure for OCGT")
                ocgt_opex = gr.Slider(minimum=0.01, maximum=0.05, value=config.OCGT_OPEX_PER_KWH, label="OCGT OPEX ($/kWh)", info="Operating expenditure for OCGT")
                ccgt_efficiency = gr.Slider(minimum=0.4, maximum=0.7, value=config.CCGT_EFFICIENCY, label="CCGT Efficiency", info="Efficiency of combined cycle gas turbine")
                ccgt_capex = gr.Slider(minimum=800, maximum=1600, value=config.CCGT_CAPEX_PER_KW, label="CCGT CAPEX ($/kW)", info="Capital expenditure for CCGT")
                ccgt_opex = gr.Slider(minimum=0.005, maximum=0.03, value=config.CCGT_OPEX_PER_KWH, label="CCGT OPEX ($/kWh)", info="Operating expenditure for CCGT")
                
                gr.Markdown("### System Parameters")
                project_lifetime = gr.Slider(minimum=10, maximum=30, value=config.PROJECT_LIFETIME, label="Project Lifetime (years)", info="Expected lifetime of the project")
                wind_battery_hours = gr.Slider(minimum=6, maximum=48, value=config.WIND_BATTERY_STORAGE_HOURS, label="Wind Battery Storage (hours)", info="Hours of battery storage for wind system")
                cutoff_day = gr.Slider(minimum=10, maximum=100, value=config.CUTOFF_DAY, label="Cutoff Day", info="Days system should handle without gas")
                hybrid_threshold = gr.Slider(minimum=0.05, maximum=0.3, value=config.HYBRID_LCOE_THRESHOLD, label="Hybrid LCOE Threshold", info="If hybrid solar + wind is not this fraction cheaper than wind or solar alone, defaults to the cheaper of wind OR solar.")

                gr.Markdown("### Financing Parameters")
                equity_premium = gr.Slider(minimum=1, maximum=10, value=config.EQUITY_PREMIUM * 100, label="Equity Premium (%)", info="Additional return beyond 20 year US bonds required for equity investment as a percentage")
                debt_premium = gr.Slider(minimum=1, maximum=10, value=config.DEBT_PREMIUM * 100, label="Debt Premium (%)", info="Additional return beyond 20 year US bonds required for debt investment as a percentage")
                debt_ratio = gr.Slider(minimum=10, maximum=90, value=config.DEBT_RATIO * 100, label="Debt Ratio (%)", info="Proportion of financing from debt as a percentage")
                tax_rate = gr.Slider(minimum=10, maximum=40, value=config.TAX_RATE * 100, label="Tax Rate (%)", info="Corporate tax rate as a percentage")

    # Connect the input_type radio button to update visibility
    input_type.change(
        fn=update_visibility,
        inputs=input_type,
        outputs=[location_column, coordinates_column]
    )
        # In your Gradio interface setup:
    submit_button.click(
        fn=analyze_energy_systems_wrapper,
        inputs=[
            input_type, location, latitude, longitude, demand_gw,
            solar_cost, wind_cost, battery_cost,
            solar_efficiency, solar_density,
            ng_price, ocgt_efficiency, ocgt_capex, ocgt_opex,
            ccgt_efficiency, ccgt_capex, ccgt_opex,
            project_lifetime, solar_battery_hours, wind_battery_hours,
            cutoff_day, hybrid_threshold,
            equity_premium, debt_premium, debt_ratio, tax_rate
        ],
        outputs=[
            solar_results, solar_energy_output, solar_capex_breakdown,
            wind_results, wind_energy_output, wind_capex_breakdown,
            ccgt_results, ccgt_cost_breakdown,
            hybrid_results, hybrid_energy_output, hybrid_capex_breakdown
        ]
    )

iface.launch()
import gradio as gr
import plotly.graph_objects as go
from solar import analyze_solar_system
from wind import analyze_wind_energy
from ccgt import analyze_ccgt
from solar_wind import analyze_hybrid_system
import config
from geopy.geocoders import Nominatim
import pandas as pd

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
    
    # Solar results
    solar_results_df = pd.DataFrame({
        'Metric': ['LCOE', 'Solar Fraction of Energy Consumed', 'Gas Fraction of Energy Consumed', 'Solar Capacity Factor', 
                   'Solar Curtailment', 'Solar Area', 'Rated Solar Capacity', 'Rated Gas Capacity', 'Capex per kW', 'Total Capex', 'WACC'],
        'Value': [f"${solar_results['lcoe']:.4f}/kWh", 
                  f"{solar_results['solar_fraction']:.2%}",
                  f"{solar_results['gas_fraction']:.2%}",
                  f"{solar_results['solar_capacity_factor']:.2%}",
                  f"{solar_results['solar_curtailment']:.2%}",
                  f"{solar_results['solar_area_km2']:.2f} km² ({solar_results['solar_area_percentage']:.2f}% of Ireland)",
                  f"{solar_results['solar_capacity_gw']:.2f} GW",
                  f"{solar_results['gas_capacity_gw']:.2f} GW",
                  f"${int(solar_results['capex_per_kw']):,.0f} $/kW",
                  f"${solar_results['total_capex']:,.0f} million",
                  f"{solar_results['wacc']:.1%}"]
    })
    
    # Update plot styling
    plot_layout = dict(
        font=dict(size=16, color='#333333'),  # Increased font size and darker color
        title_font_size=20,  # Increased title font size
        legend=dict(font=dict(size=14)),  # Increased legend font size
        plot_bgcolor='rgba(240,240,240,0.5)',  # Light gray background
        paper_bgcolor='rgba(240,240,240,0.5)',  # Light gray background
    )
    
    # Color palette (adjusted for better visibility)
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']

    # Solar energy generated plot
    solar_energy_fig = go.Figure()
    solar_energy_fig.add_trace(go.Bar(x=list(range(len(solar_results['energy_generated_data']['solar_generated']))), 
                                      y=solar_results['energy_generated_data']['solar_generated'], 
                                      name='Solar Output', 
                                      marker_color=colors[0]))
    solar_energy_fig.add_trace(go.Bar(x=list(range(len(solar_results['energy_generated_data']['gas_generated']))), 
                                      y=solar_results['energy_generated_data']['gas_generated'], 
                                      name='Gas Output', 
                                      marker_color=colors[1]))
    solar_energy_fig.update_layout(
        title=f'Daily Energy Output at {lat:.2f}, {lon:.2f}: Solar + Gas',
        xaxis_title='Days (sorted by solar generated)',
        yaxis_title='Energy Output (kWh)',
        barmode='stack',
        **plot_layout
    )

    # Solar capex breakdown plot
    solar_capex_fig = go.Figure(data=[go.Pie(
        labels=solar_results['capex_breakdown_data']['components'],
        values=solar_results['capex_breakdown_data']['values'],
        marker_colors=colors[:3]
    )])
    solar_capex_fig.update_layout(
        title=f'Capex Breakdown for Solar + Gas System',
        **plot_layout
    )

    # Wind analysis
    wind_results = analyze_wind_energy(lat, lon, daily_usage, demand_kw, cutoff_day)
    
    # Wind results
    wind_results_df = pd.DataFrame({
        'Metric': ['LCOE', 'Wind Fraction of Energy Consumed', 'Gas Fraction of Energy Consumed', 'Wind Capacity Factor', 
                'Wind Curtailment', 'Rated Wind Capacity', 'Rated Gas Capacity', 'Capex per kW', 'Total Capex', 'WACC'],
        'Value': [f"${wind_results['lcoe']:.4f}/kWh", 
                f"{wind_results['wind_fraction']:.2%}",
                f"{wind_results['gas_fraction']:.2%}",
                f"{wind_results['wind_capacity_factor']:.2%}",
                f"{wind_results['wind_curtailment']:.2%}",
                f"{wind_results['wind_capacity_gw']:.2f} GW",
                f"{wind_results['gas_capacity_gw']:.2f} GW",
                f"${int(wind_results['capex_per_kw']):,.0f} $/kW",
                f"${int(wind_results['total_capex']):,.0f} million",
                f"{wind_results['wacc']:.1%}"]
    })
    
    # Wind energy generated plot
    wind_energy_fig = go.Figure()
    wind_energy_fig.add_trace(go.Bar(x=list(range(len(wind_results['energy_generated_data']['wind_generated']))), 
                                     y=wind_results['energy_generated_data']['wind_generated'], 
                                     name='Wind Output', 
                                     marker_color=colors[2]))
    wind_energy_fig.add_trace(go.Bar(x=list(range(len(wind_results['energy_generated_data']['gas_generated']))), 
                                     y=wind_results['energy_generated_data']['gas_generated'], 
                                     name='Gas Output', 
                                     marker_color=colors[1]))
    wind_energy_fig.update_layout(
        title=f'Daily Energy Output at {lat:.2f}, {lon:.2f}: Wind + Gas',
        xaxis_title='Days (sorted by wind generated)',
        yaxis_title='Energy Output (kWh)',
        barmode='stack',
        **plot_layout
    )

    # Wind capex breakdown plot
    wind_capex_fig = go.Figure(data=[go.Pie(
        labels=wind_results['capex_breakdown_data']['components'],
        values=wind_results['capex_breakdown_data']['values'],
        marker_colors=colors[:3]
    )])
    wind_capex_fig.update_layout(
        title=f'Capex Breakdown for Wind + Gas System',
        **plot_layout
    )

    # CCGT analysis
    ccgt_results = analyze_ccgt(daily_usage, demand_kw)
    
    # CCGT results
    ccgt_results_df = pd.DataFrame({
        'Metric': ['LCOE', 'Capacity', 'Capex per kW', 'Total Capex', 
                   'Annual Energy Consumed', 'WACC'],
        'Value': [f"${ccgt_results['lcoe']:.4f}/kWh",
                  f"{ccgt_results['capacity_gw']:.2f} GW",
                  f"${ccgt_results['capex_per_kw']:.2f}/kW",
                  f"${ccgt_results['total_capex']:,.0f}",
                  f"{ccgt_results['annual_energy_used']:,.0f} kWh",
                  f"{ccgt_results['wacc']:.1%}"]
    })
    
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
    
    # Hybrid results
    hybrid_results_df = pd.DataFrame({
        'Metric': ['LCOE', 'Solar as fraction of solar + wind', 'Wind as fraction of solar + wind', 'Gas fraction of energy consumed', 
                   'Solar Capacity Factor', 'Solar Curtailment', 'Wind Capacity Factor', 'Wind Curtailment', 'Solar Capacity', 
                   'Wind Capacity', 'Gas Capacity', 'Battery Capacity', 'Capex per kW', 'Total Capex', 'WACC'],
        'Value': [f"${hybrid_results['lcoe']:.4f}/kWh",
                  f"{hybrid_results['solar_fraction']:.2%}",
                  f"{hybrid_results['wind_fraction']:.2%}",
                  f"{hybrid_results['gas_fraction']:.2%}",
                  f"{hybrid_results['solar_capacity_factor']:.2%}",
                  f"{hybrid_results['solar_curtailment']:.2%}",
                  f"{hybrid_results['wind_capacity_factor']:.2%}",
                  f"{hybrid_results['wind_curtailment']:.2%}",
                  f"{hybrid_results['solar_capacity_gw']:.2f} GW",
                  f"{hybrid_results['wind_capacity_gw']:.2f} GW",
                  f"{hybrid_results['gas_capacity_gw']:.2f} GW",
                  f"{hybrid_results['battery_capacity_gwh']:.2f} GWh",
                  f"${int(hybrid_results['capex_per_kw']):,.0f}/kW",
                  f"${int(hybrid_results['total_capex']):,.0f} million",
                  f"{hybrid_results['wacc']:.1%}"]
    })
    
    # Hybrid energy generated plot
    hybrid_energy_fig = go.Figure()
    hybrid_energy_fig.add_trace(go.Bar(x=list(range(len(hybrid_results['energy_generated_data']['solar_generated']))), 
                                       y=hybrid_results['energy_generated_data']['solar_generated'], 
                                       name='Solar Output', 
                                       marker_color=colors[0]))
    hybrid_energy_fig.add_trace(go.Bar(x=list(range(len(hybrid_results['energy_generated_data']['wind_generated']))), 
                                       y=hybrid_results['energy_generated_data']['wind_generated'], 
                                       name='Wind Output', 
                                       marker_color=colors[2]))
    hybrid_energy_fig.add_trace(go.Bar(x=list(range(len(hybrid_results['energy_generated_data']['gas_generated']))), 
                                       y=hybrid_results['energy_generated_data']['gas_generated'], 
                                       name='Gas Output', 
                                       marker_color=colors[1]))
    hybrid_energy_fig.update_layout(
        title=f'Daily Energy Output at {lat:.2f}, {lon:.2f}: Solar, Wind, and Gas',
        xaxis_title='Days (sorted by combined generated)',
        yaxis_title='Energy Output (kWh)',
        barmode='stack',
        **plot_layout
    )

    # Hybrid capex breakdown plot
    hybrid_capex_fig = go.Figure(data=[go.Pie(
        labels=hybrid_results['capex_breakdown_data']['components'],
        values=hybrid_results['capex_breakdown_data']['values'],
        marker_colors=colors[:4]
    )])
    hybrid_capex_fig.update_layout(
        title=f'Capex Breakdown for {hybrid_results["system_type"]} System',
        **plot_layout
    )

    # Create the LCOE vs Solar Fraction plot using Plotly
    lcoe_vs_solar_fraction_fig = go.Figure()
    lcoe_vs_solar_fraction_fig.add_trace(go.Scatter(
        x=hybrid_results['lcoe_vs_solar_fraction_data']['solar_fractions'],
        y=hybrid_results['lcoe_vs_solar_fraction_data']['lcoe_values'],
        mode='lines+markers',
        line=dict(color=colors[0]),
        marker=dict(color=colors[1])
    ))
    lcoe_vs_solar_fraction_fig.update_layout(
        title='LCOE vs Solar Fraction (of Solar + Wind)',
        xaxis_title='Solar Fraction (of Solar + Wind)',
        yaxis_title='LCOE ($/kWh)',
        yaxis=dict(range=[0, max(hybrid_results['lcoe_vs_solar_fraction_data']['lcoe_values']) * 1.1]),  # Start at 0, end slightly above max value
        **plot_layout
    )

    return (solar_results_df, solar_energy_fig, solar_capex_fig,
            wind_results_df, wind_energy_fig, wind_capex_fig,
            ccgt_results_df, ccgt_cost_fig,
            hybrid_results_df, hybrid_energy_fig, hybrid_capex_fig,
            lcoe_vs_solar_fraction_fig)  # Return the Plotly figure instead of an image

import traceback

def analyze_energy_systems_wrapper(input_type, location, lat, lon, demand_gw, *args):
    try:
        if input_type == "Location":
            coordinates = get_coordinates(location)
            if coordinates:
                lat, lon = coordinates
                print(f"Coordinates found for location: {lat}, {lon}")
            else:
                return "Location not found. Please try a more specific location or use latitude and longitude.", None, None, None, None, None, None, None, None, None, None, None
        elif input_type == "Coordinates":
            coordinates = validate_coordinates(lat, lon)
            if coordinates:
                lat, lon = coordinates
                print(f"Using provided coordinates: {lat}, {lon}")
            else:
                return "Invalid latitude or longitude. Please enter valid coordinates.", None, None, None, None, None, None, None, None, None, None, None
        else:
            return "Please select either location or coordinates input method.", None, None, None, None, None, None, None, None, None, None, None
        
        return analyze_energy_systems(lat, lon, demand_gw, *args)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(error_message)  # Print the error for debugging
        # Return the error message as the first item, and None for all other outputs
        return [error_message] + [None] * 11

def update_visibility(choice):
    return (
        gr.update(visible=(choice == "Location")),
        gr.update(visible=(choice == "Coordinates"))
    )

with gr.Blocks() as iface:
    gr.Markdown("# Gigawatt Data Center - Energy System Analysis", elem_classes="text-2xl")
    gr.Markdown("Built by [Ronan McGovern](http://RonanMcGovern.com/About)", elem_classes="text-xl")
    gr.Markdown("Design approach:", elem_classes="text-xl")
    gr.Markdown("- Select between wind, solar, wind + solar, or gas (combined cycle)", elem_classes="text-lg")
    gr.Markdown("- Geo coordinates are used to calculate local wind speeds and solar irradiation on an hourly basis across the 2022 calendar year.", elem_classes="text-lg")
    gr.Markdown("- For wind/solar/wind+solar, an open cycle gas turbine is used to balance load for a max of 50 days per year.", elem_classes="text-lg")
    gr.Markdown("- The solar + wind hybrid system shown is that which minimises the levelised cost of energy. Typically this resolves to a pure solar (+ gas) or pure wind (+ gas) system.", elem_classes="text-lg")
    gr.Markdown("- All $/kW costs are on an installed basis.", elem_classes="text-lg")

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
    
    submit_button = gr.Button("Analyse")

    with gr.Tabs() as tabs:
        with gr.Tab("Solar Analysis Results", id="solar"):
            solar_results = gr.Dataframe(label="Key Results")
            solar_energy_generated = gr.Plot(label="Energy Output")
            solar_capex_breakdown = gr.Plot(label="Capex Breakdown")
        
        with gr.Tab("Wind Analysis Results", id="wind"):
            wind_results = gr.Dataframe(label="Key Results")
            wind_energy_generated = gr.Plot(label="Energy Output")
            wind_capex_breakdown = gr.Plot(label="Capex Breakdown")
        
        with gr.Tab("Hybrid System Analysis Results", id="hybrid"):
            hybrid_results = gr.Dataframe(label="Key Results")
            hybrid_energy_generated = gr.Plot(label="Energy Output")
            hybrid_capex_breakdown = gr.Plot(label="Capex Breakdown")
            lcoe_vs_solar_fraction_plot = gr.Plot(label="LCOE vs Solar Fraction")

        with gr.Tab("CCGT Analysis Results", id="ccgt"):
            ccgt_results = gr.Dataframe(label="Key Results")
            ccgt_cost_breakdown = gr.Plot(label="Annual Cost Breakdown")

        with gr.Tab("Advanced Settings", id="advanced"):
            with gr.Column():
                gr.Markdown("### Battery Parameters")
                battery_cost = gr.Slider(minimum=100, maximum=500, value=config.BATTERY_COST_PER_KWH, label="Battery Cost ($/kWh)", info="Cost per kWh of battery storage")

                gr.Markdown("### Solar Parameters")
                solar_cost = gr.Slider(minimum=100, maximum=1000, value=config.SOLAR_COST_PER_KW, label="Solar Cost ($/kW)", info="Cost per kW of solar installation")
                solar_efficiency = gr.Slider(minimum=0.1, maximum=0.3, value=config.SOLAR_PANEL_EFFICIENCY, label="Solar Panel Efficiency", info="Efficiency of solar panels")
                solar_density = gr.Slider(minimum=0.2, maximum=0.6, value=config.SOLAR_PANEL_DENSITY, label="Solar Panel Density", info="m² of panel area per m² of land")
                solar_battery_hours = gr.Slider(minimum=6, maximum=48, value=config.SOLAR_BATTERY_STORAGE_HOURS, label="Solar Battery Storage (hours)", info="Hours of battery storage for solar system")
                
                gr.Markdown("### Wind Parameters")
                wind_cost = gr.Slider(minimum=500, maximum=2000, value=config.WIND_COST_PER_KW, label="Wind Cost ($/kW)", info="Cost per kW of wind installation")
                wind_battery_hours = gr.Slider(minimum=6, maximum=48, value=config.WIND_BATTERY_STORAGE_HOURS, label="Wind Battery Storage (hours)", info="Hours of battery storage for wind system")

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
        fn=lambda *args: analyze_energy_systems_wrapper(*args),
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
            solar_results, solar_energy_generated, solar_capex_breakdown,
            wind_results, wind_energy_generated, wind_capex_breakdown,
            ccgt_results, ccgt_cost_breakdown,
            hybrid_results, hybrid_energy_generated, hybrid_capex_breakdown,
            lcoe_vs_solar_fraction_plot
        ]
    )

    iface.load(lambda: gr.Tabs(selected="solar"))

iface.launch()
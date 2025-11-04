"use client"

import type React from "react"

import { useEffect, useState } from "react"
import TemperatureGraph from "../components/graphDisplay"
import RawDataDisplay from "../components/rawDataDisplay"
import StatsDisplay from "../components/statsDisplay"
import { AlertCircle } from "lucide-react"
import { submitSimulation, getJobResults, getCityCoordinates } from "../lib/api"

// Updated interface to match the actual API response format
interface TemperatureDataPoint {
  datetime: string
  Tin: number
  Tout: number
  T_mass?: number
  T_soil?: number
  Q_heater?: number
  Q_latent?: number
  Q_to_threshold?: number
}

export default function TemperatureAnalysisDashboard() {
  // Basic parameters
  const [city, setCity] = useState("")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  
  // Geometry parameters
  const [A_glass, setA_glass] = useState(50.0)
  const [V, setV] = useState(100.0)
  const [A_floor, setA_floor] = useState(50.0)
  
  // Thermal properties
  const [tau_glass, setTau_glass] = useState(0.85)
  const [fraction_solar_to_air, setFraction_solar_to_air] = useState(0.3)
  const [U_day, setU_day] = useState(2.0)
  const [U_night, setU_night] = useState(1.5)
  
  // Ventilation
  const [ACH, setACH] = useState(0.5)
  
  // Thermal mass
  const [thermal_mass_kg, setThermal_mass_kg] = useState(40000.0)
  const [cp_mass, setCp_mass] = useState(4186.0)
  const [A_mass, setA_mass] = useState(40.0)
  const [h_am, setH_am] = useState(5.0)
  
  // Heating
  const [heater_max_w, setHeater_max_w] = useState(5000.0)
  const [heating_rate_factor, setHeating_rate_factor] = useState(0.3)
  const [setpoint, setSetpoint] = useState<number | null>(10.0)
  
  // Initial temperatures
  const [T_init, setT_init] = useState(15.0)
  const [T_mass_init, setT_mass_init] = useState(15.0)
  const [T_soil_init, setT_soil_init] = useState(15.0)
  
  const [temperatureData, setTemperatureData] = useState<TemperatureDataPoint[]>([])
  const [visibleData, setVisibleData] = useState<TemperatureDataPoint[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // When temperature data changes, update visible data
  useEffect(() => {
    setVisibleData(temperatureData)
  }, [temperatureData])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validate inputs
    if (!city) {
      setError("Please enter a city")
      return
    }

    if (!startDate) {
      setError("Please enter a start date")
      return
    }

    if (!endDate) {
      setError("Please enter an end date")
      return
    }

    // Validate date range
    const start = new Date(startDate)
    const end = new Date(endDate)

    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
      setError("Please enter valid dates")
      return
    }

    if (end < start) {
      setError("End date must be after start date")
      return
    }

    // Calculate date difference
    const diffTime = Math.abs(end.getTime() - start.getTime())
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

    // Optional: Add a warning for large date ranges
    if (diffDays > 30 && !confirm(`You've selected a ${diffDays} day range. This might be slow to load. Continue?`)) {
      return
    }

    setIsLoading(true)

    try {
      // Convert city name to coordinates
      const coords = getCityCoordinates(city)
      if (!coords) {
        setError(`City "${city}" not found. Please use a major US city or enter coordinates manually.`)
        setIsLoading(false)
        return
      }

      // Submit simulation job with all parameters
      console.log("Submitting simulation job...")
      const jobResponse = await submitSimulation({
        lat: coords.lat,
        lon: coords.lon,
        start_date: startDate,
        end_date: endDate,
        A_glass,
        V,
        A_floor,
        tau_glass,
        fraction_solar_to_air,
        U_day,
        U_night,
        ACH,
        thermal_mass_kg,
        cp_mass,
        A_mass,
        h_am,
        heater_max_w,
        heating_rate_factor,
        setpoint: setpoint || undefined,
        T_init,
        T_mass_init,
        T_soil_init,
      })

      console.log("Job submitted:", jobResponse)
      const jobId = jobResponse.job_id

      // Poll for results
      console.log("Waiting for job to complete...")
      const results = await getJobResults(jobId, 120000) // 2 minute timeout

      if (!results.result || !results.result.data) {
        throw new Error("No data in results")
      }

      // Debug: Log raw API response
      console.log("Raw API response:", results.result)
      if (results.result.data && results.result.data.length > 0) {
        console.log("First data point from API:", results.result.data[0])
        console.log("Tout in first point:", results.result.data[0].Tout, typeof results.result.data[0].Tout)
      }

      // Transform API response to match expected format
      const data: TemperatureDataPoint[] = results.result.data.map((row: any) => {
        // Ensure Tout is properly parsed
        let tout = 0
        if (row.Tout !== undefined && row.Tout !== null) {
          if (typeof row.Tout === 'number') {
            tout = row.Tout
          } else if (typeof row.Tout === 'string') {
            tout = parseFloat(row.Tout) || 0
          } else {
            tout = Number(row.Tout) || 0
          }
        }
        
        return {
          datetime: row.datetime,
          Tin: typeof row.Tin === 'number' ? row.Tin : (parseFloat(row.Tin) || 0),
          Tout: tout,
          T_mass: typeof row.T_mass === 'number' ? row.T_mass : (row.T_mass ? parseFloat(row.T_mass) : undefined),
          T_soil: typeof row.T_soil === 'number' ? row.T_soil : (row.T_soil ? parseFloat(row.T_soil) : undefined),
          Q_heater: typeof row.Q_heater === 'number' ? row.Q_heater : (row.Q_heater ? parseFloat(row.Q_heater) : undefined),
          Q_latent: typeof row.Q_latent === 'number' ? row.Q_latent : (row.Q_latent ? parseFloat(row.Q_latent) : undefined),
          Q_to_threshold: typeof row.Q_to_threshold === 'number' ? row.Q_to_threshold : (row.Q_to_threshold ? parseFloat(row.Q_to_threshold) : undefined),
        }
      })

      console.log("Data received:", data)
      console.log(`Received ${data.length} data points spanning ${diffDays} days`)
      if (data.length > 0) {
        console.log("Sample data point:", data[0])
        console.log("Tout values:", data.map(d => d.Tout).slice(0, 10))
      }

      if (data.length === 0) {
        setError("No data returned for the selected date range")
      } else {
        setTemperatureData(data)
        setVisibleData(data) // Initialize visible data with all data
      }
    } catch (error) {
      console.error("Error fetching temperature data:", error)
      setError(`Failed to fetch temperature data: ${error instanceof Error ? error.message : "Unknown error"}`)
      setTemperatureData([])
      setVisibleData([])
    } finally {
      setIsLoading(false)
    }
  }

  // Handle visible data change from graph component
  const handleVisibleDataChange = (data: TemperatureDataPoint[]) => {
    setVisibleData(data)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* INPUT SECTION */}
      <div className="lg:col-span-1 bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">INPUT</h2>
        </div>
        <div className="p-4 overflow-y-auto flex-1">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label htmlFor="city" className="block text-sm font-medium text-gray-700">
                City
              </label>
              <input
                id="city"
                type="text"
                placeholder="Enter city name (e.g., New York, Tokyo)"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="startDate" className="block text-sm font-medium text-gray-700">
                Start Date
              </label>
              <input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="endDate" className="block text-sm font-medium text-gray-700">
                End Date
              </label>
              <input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Geometry Parameters */}
            <div className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Geometry</h3>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label htmlFor="A_glass" className="block text-xs font-medium text-gray-600">
                    Glass Area (m²)
                  </label>
                  <input
                    id="A_glass"
                    type="number"
                    min="0"
                    step="0.1"
                    value={A_glass}
                    onChange={(e) => setA_glass(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="V" className="block text-xs font-medium text-gray-600">
                    Volume (m³)
                  </label>
                  <input
                    id="V"
                    type="number"
                    min="0"
                    step="0.1"
                    value={V}
                    onChange={(e) => setV(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="A_floor" className="block text-xs font-medium text-gray-600">
                    Floor Area (m²)
                  </label>
                  <input
                    id="A_floor"
                    type="number"
                    min="0"
                    step="0.1"
                    value={A_floor}
                    onChange={(e) => setA_floor(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Thermal Properties */}
            <div className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Thermal Properties</h3>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label htmlFor="tau_glass" className="block text-xs font-medium text-gray-600">
                    Glass Transmissivity (τ)
                  </label>
                  <input
                    id="tau_glass"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={tau_glass}
                    onChange={(e) => setTau_glass(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="fraction_solar_to_air" className="block text-xs font-medium text-gray-600">
                    Fraction Solar to Air
                  </label>
                  <input
                    id="fraction_solar_to_air"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={fraction_solar_to_air}
                    onChange={(e) => setFraction_solar_to_air(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="U_day" className="block text-xs font-medium text-gray-600">
                    U-value Day (W/m²K)
                  </label>
                  <input
                    id="U_day"
                    type="number"
                    min="0"
                    step="0.1"
                    value={U_day}
                    onChange={(e) => setU_day(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="U_night" className="block text-xs font-medium text-gray-600">
                    U-value Night (W/m²K)
                  </label>
                  <input
                    id="U_night"
                    type="number"
                    min="0"
                    step="0.1"
                    value={U_night}
                    onChange={(e) => setU_night(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Ventilation */}
            <div className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Ventilation</h3>
              <div className="space-y-1">
                <label htmlFor="ACH" className="block text-xs font-medium text-gray-600">
                  Air Changes per Hour (ACH)
                </label>
                <input
                  id="ACH"
                  type="number"
                  min="0"
                  step="0.1"
                  value={ACH}
                  onChange={(e) => setACH(parseFloat(e.target.value) || 0)}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Thermal Mass */}
            <div className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Thermal Mass</h3>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label htmlFor="thermal_mass_kg" className="block text-xs font-medium text-gray-600">
                    Thermal Mass (kg)
                  </label>
                  <input
                    id="thermal_mass_kg"
                    type="number"
                    min="0"
                    step="100"
                    value={thermal_mass_kg}
                    onChange={(e) => setThermal_mass_kg(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="cp_mass" className="block text-xs font-medium text-gray-600">
                    Specific Heat (J/kgK)
                  </label>
                  <input
                    id="cp_mass"
                    type="number"
                    min="0"
                    step="100"
                    value={cp_mass}
                    onChange={(e) => setCp_mass(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="A_mass" className="block text-xs font-medium text-gray-600">
                    Mass Area (m²)
                  </label>
                  <input
                    id="A_mass"
                    type="number"
                    min="0"
                    step="0.1"
                    value={A_mass}
                    onChange={(e) => setA_mass(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="h_am" className="block text-xs font-medium text-gray-600">
                    Heat Transfer Coeff. (W/m²K)
                  </label>
                  <input
                    id="h_am"
                    type="number"
                    min="0"
                    step="0.1"
                    value={h_am}
                    onChange={(e) => setH_am(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Heating */}
            <div className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Heating</h3>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label htmlFor="heater_max_w" className="block text-xs font-medium text-gray-600">
                    Max Heater Power (W)
                  </label>
                  <input
                    id="heater_max_w"
                    type="number"
                    min="0"
                    step="100"
                    value={heater_max_w}
                    onChange={(e) => setHeater_max_w(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="heating_rate_factor" className="block text-xs font-medium text-gray-600">
                    Heating Rate Factor
                  </label>
                  <input
                    id="heating_rate_factor"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={heating_rate_factor}
                    onChange={(e) => setHeating_rate_factor(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="setpoint" className="block text-xs font-medium text-gray-600">
                    Setpoint Temperature (°C)
                  </label>
                  <input
                    id="setpoint"
                    type="number"
                    step="0.1"
                    value={setpoint ?? ""}
                    onChange={(e) => setSetpoint(e.target.value ? parseFloat(e.target.value) : null)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                    placeholder="Leave empty to disable"
                  />
                  <div className="text-xs text-gray-500">Leave empty to disable heating</div>
                </div>
              </div>
            </div>

            {/* Initial Temperatures */}
            <div className="border-t border-gray-200 pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Initial Temperatures (°C)</h3>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label htmlFor="T_init" className="block text-xs font-medium text-gray-600">
                    Air Temperature
                  </label>
                  <input
                    id="T_init"
                    type="number"
                    step="0.1"
                    value={T_init}
                    onChange={(e) => setT_init(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="T_mass_init" className="block text-xs font-medium text-gray-600">
                    Thermal Mass Temperature
                  </label>
                  <input
                    id="T_mass_init"
                    type="number"
                    step="0.1"
                    value={T_mass_init}
                    onChange={(e) => setT_mass_init(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label htmlFor="T_soil_init" className="block text-xs font-medium text-gray-600">
                    Soil Temperature
                  </label>
                  <input
                    id="T_soil_init"
                    type="number"
                    step="0.1"
                    value={T_soil_init}
                    onChange={(e) => setT_soil_init(parseFloat(e.target.value) || 0)}
                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-col space-y-2">
              <span className="text-sm text-gray-500">Date Range Presets:</span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const today = new Date()
                    const yesterday = new Date(today)
                    yesterday.setDate(yesterday.getDate() - 1)
                    setStartDate(yesterday.toISOString().split("T")[0])
                    setEndDate(today.toISOString().split("T")[0])
                  }}
                  className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                >
                  Last 24h
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const today = new Date()
                    const weekAgo = new Date(today)
                    weekAgo.setDate(weekAgo.getDate() - 7)
                    setStartDate(weekAgo.toISOString().split("T")[0])
                    setEndDate(today.toISOString().split("T")[0])
                  }}
                  className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                >
                  Last 7 days
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const today = new Date()
                    const monthAgo = new Date(today)
                    monthAgo.setDate(monthAgo.getDate() - 30)
                    setStartDate(monthAgo.toISOString().split("T")[0])
                    setEndDate(today.toISOString().split("T")[0])
                  }}
                  className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                >
                  Last 30 days
                </button>
              </div>
            </div>

            {error && (
              <div className="text-red-500 text-sm p-3 bg-red-50 border border-red-200 rounded flex items-start">
                <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md shadow transition-colors duration-200 ease-in-out disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-blue-600"
              disabled={isLoading}
            >
              {isLoading ? "Loading..." : "Analyze Temperature"}
            </button>
          </form>
        </div>
      </div>

      {/* RIGHT COLUMN - GRAPH AND RAW DATA */}
      <div className="lg:col-span-2 space-y-4">
        {/* STATISTICS SECTION */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold">STATISTICS</h2>
          </div>
          <div className="p-4">
            <StatsDisplay data={visibleData} />
          </div>
        </div>

        {/* GRAPH SECTION */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold">GRAPH</h2>
          </div>
          <div className="p-4">
            <TemperatureGraph data={temperatureData} onVisibleDataChange={handleVisibleDataChange} />
          </div>
        </div>

        {/* RAW DATA SECTION */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold">RAW DATA</h2>
          </div>
          <div className="p-4">
            <RawDataDisplay data={temperatureData} />
          </div>
        </div>
      </div>
    </div>
  )
}
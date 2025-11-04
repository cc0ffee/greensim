"use client"

import { useState, useEffect } from "react"
import { ArrowUp, ArrowDown, Thermometer } from "lucide-react"

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

interface TemperatureStatisticsProps {
  data: TemperatureDataPoint[]
}

interface Statistics {
  internal: {
    min: number
    max: number
    avg: number
  }
  external: {
    min: number
    max: number
    avg: number
  }
  dayCount: number
}

export default function TemperatureStatistics({ data }: TemperatureStatisticsProps) {
  const [stats, setStats] = useState<Statistics | null>(null)

  // Calculate statistics when data changes
  useEffect(() => {
    if (!data || data.length === 0) {
      setStats(null)
      return
    }

    // Calculate statistics
    const internalTemps = data.map((item) => item.Tin)
    const externalTemps = data.map((item) => item.Tout)

    // Calculate unique days
    const uniqueDays = new Set(
      data.map((item) => {
        const date = new Date(item.datetime.replace(" ", "T"))
        return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`
      }),
    )

    setStats({
      internal: {
        min: Math.min(...internalTemps),
        max: Math.max(...internalTemps),
        avg: internalTemps.reduce((sum, temp) => sum + temp, 0) / internalTemps.length,
      },
      external: {
        min: Math.min(...externalTemps),
        max: Math.max(...externalTemps),
        avg: externalTemps.reduce((sum, temp) => sum + temp, 0) / externalTemps.length,
      },
      dayCount: uniqueDays.size,
    })
  }, [data])

  // Function to convert Celsius to Fahrenheit
  const celsiusToFahrenheit = (celsius: number): number => {
    return (celsius * 9) / 5 + 32
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-[100px] bg-gray-100 rounded-md">
        <p className="text-gray-500">No data available for statistics</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Internal Temperature Stats */}
      <div className="bg-white rounded-lg border border-blue-200 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium text-blue-700">Internal Temperature</h3>
          <Thermometer className="h-5 w-5 text-blue-500" />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="flex items-center space-x-2 bg-blue-50 rounded p-2">
            <div className="h-4 w-4 text-blue-600 flex-shrink-0">•</div>
            <div>
              <div className="text-xs text-blue-600 uppercase font-semibold">Average</div>
              <div className="font-bold text-blue-800">
                {stats.internal.avg.toFixed(1)}°C
                <span className="text-sm font-normal text-blue-600 block">
                  {celsiusToFahrenheit(stats.internal.avg).toFixed(1)}°F
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 bg-blue-50 rounded p-2">
            <ArrowUp className="h-4 w-4 text-red-500 flex-shrink-0" />
            <div>
              <div className="text-xs text-blue-600 uppercase font-semibold">Max</div>
              <div className="font-bold text-blue-800">
                {stats.internal.max.toFixed(1)}°C
                <span className="text-sm font-normal text-blue-600 block">
                  {celsiusToFahrenheit(stats.internal.max).toFixed(1)}°F
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 bg-blue-50 rounded p-2">
            <ArrowDown className="h-4 w-4 text-blue-500 flex-shrink-0" />
            <div>
              <div className="text-xs text-blue-600 uppercase font-semibold">Min</div>
              <div className="font-bold text-blue-800">
                {stats.internal.min.toFixed(1)}°C
                <span className="text-sm font-normal text-blue-600 block">
                  {celsiusToFahrenheit(stats.internal.min).toFixed(1)}°F
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* External Temperature Stats */}
      <div className="bg-white rounded-lg border border-red-200 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium text-red-700">External Temperature</h3>
          <Thermometer className="h-5 w-5 text-red-500" />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="flex items-center space-x-2 bg-red-50 rounded p-2">
            <div className="h-4 w-4 text-red-600 flex-shrink-0">•</div>
            <div>
              <div className="text-xs text-red-600 uppercase font-semibold">Average</div>
              <div className="font-bold text-red-800">
                {stats.external.avg.toFixed(1)}°C
                <span className="text-sm font-normal text-red-600 block">
                  {celsiusToFahrenheit(stats.external.avg).toFixed(1)}°F
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 bg-red-50 rounded p-2">
            <ArrowUp className="h-4 w-4 text-red-500 flex-shrink-0" />
            <div>
              <div className="text-xs text-red-600 uppercase font-semibold">Max</div>
              <div className="font-bold text-red-800">
                {stats.external.max.toFixed(1)}°C
                <span className="text-sm font-normal text-red-600 block">
                  {celsiusToFahrenheit(stats.external.max).toFixed(1)}°F
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 bg-red-50 rounded p-2">
            <ArrowDown className="h-4 w-4 text-blue-500 flex-shrink-0" />
            <div>
              <div className="text-xs text-red-600 uppercase font-semibold">Min</div>
              <div className="font-bold text-red-800">
                {stats.external.min.toFixed(1)}°C
                <span className="text-sm font-normal text-red-600 block">
                  {celsiusToFahrenheit(stats.external.min).toFixed(1)}°F
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

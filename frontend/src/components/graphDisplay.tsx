"use client"

import { useState, useEffect, useRef } from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  ReferenceArea,
} from "recharts"
import { ZoomIn, ZoomOut, RefreshCw } from "lucide-react"

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

interface FormattedDataPoint extends TemperatureDataPoint {
  formattedTime: string
  sortTime: number
  timestamp?: Date 
  index: number
}

export default function TemperatureGraph({
  data,
  onVisibleDataChange,
}: {
  data: TemperatureDataPoint[]
  onVisibleDataChange?: (visibleData: TemperatureDataPoint[]) => void
}) {
  // State for zooming and selection
  const [leftIndex, setLeftIndex] = useState<number | null>(null)
  const [rightIndex, setRightIndex] = useState<number | null>(null)
  const [refAreaLeft, setRefAreaLeft] = useState<string | null>(null)
  const [refAreaRight, setRefAreaRight] = useState<string | null>(null)
  const [zoomedData, setZoomedData] = useState<FormattedDataPoint[]>([])
  const [isZoomed, setIsZoomed] = useState(false)
  const chartRef = useRef<HTMLDivElement>(null)

  // Format and sort timestamps for better display
  const formattedData: FormattedDataPoint[] = data
    .map((item, index) => {
      try {
        // Parse the timestamp (format: "YYYY-MM-DD HH:MM:SS" or ISO format)
        const timestamp = new Date(item.datetime.replace(" ", "T"))

        // Check if the timestamp is valid
        if (isNaN(timestamp.getTime())) {
          console.warn("Invalid timestamp:", item.datetime)
          return {
            ...item,
            formattedTime: `Invalid-${index}`, // Use index to ensure uniqueness
            sortTime: index, // Use index as fallback sort value
            index,
          }
        }

        // Format for display
        const formattedTime = timestamp.toLocaleString("en-US", {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })

        return {
          ...item,
          formattedTime,
          sortTime: timestamp.getTime(), // Use for sorting
          timestamp, // Store the actual Date object
          index,
        }
      } catch (error) {
        console.error("Error formatting timestamp:", error)
        return {
          ...item,
          formattedTime: `Error-${index}`, // Use index to ensure uniqueness
          sortTime: index, // Use index as fallback sort value
          index,
        }
      }
    })
    .sort((a, b) => a.sortTime - b.sortTime) // Sort chronologically

  // Initialize zoomed data with full data
  useEffect(() => {
    setZoomedData(formattedData)
    setIsZoomed(false)

    // Debug: Log sample data to check Tout values
    if (formattedData.length > 0) {
      console.log("Graph data sample:", formattedData[0])
      console.log("Tout values in graph:", formattedData.slice(0, 5).map(d => ({ datetime: d.datetime, Tout: d.Tout })))
    }

    // Notify parent component about the visible data
    if (onVisibleDataChange) {
      // Convert FormattedDataPoint back to TemperatureDataPoint for the parent component
      const visibleData: TemperatureDataPoint[] = formattedData.map((item) => ({
        datetime: item.datetime,
        Tin: item.Tin,
        Tout: item.Tout,
        T_mass: item.T_mass,
        T_soil: item.T_soil,
        Q_heater: item.Q_heater,
        Q_latent: item.Q_latent,
        Q_to_threshold: item.Q_to_threshold,
      }))
      onVisibleDataChange(visibleData)
    }
  }, [data, onVisibleDataChange])

  // Notify parent component when zoomed data changes
  useEffect(() => {
    if (onVisibleDataChange) {
      // Convert FormattedDataPoint back to TemperatureDataPoint for the parent component
      const visibleData: TemperatureDataPoint[] = zoomedData.map((item) => ({
        datetime: item.datetime,
        Tin: item.Tin,
        Tout: item.Tout,
        T_mass: item.T_mass,
        T_soil: item.T_soil,
        Q_heater: item.Q_heater,
        Q_latent: item.Q_latent,
        Q_to_threshold: item.Q_to_threshold,
      }))
      onVisibleDataChange(visibleData)
    }
  }, [zoomedData, onVisibleDataChange])

  // Calculate the number of days in the data
  const dayCount = (() => {
    if (zoomedData.length === 0) return 0

    const dates = new Set<string>()
    zoomedData.forEach((item) => {
      // Check if timestamp exists and is a valid Date object
      if (item.timestamp && item.timestamp instanceof Date) {
        const dateStr = item.timestamp.toISOString().split("T")[0]
        dates.add(dateStr)
      }
    })

    return dates.size
  })()

  // Convert 40°F to Celsius: (40 - 32) * 5/9 = 4.44°C
  const idealTemperatureCelsius = 4.44

  // Mouse down handler for selection
  const handleMouseDown = (e: any) => {
    if (!e || !e.activeLabel) return
    setRefAreaLeft(e.activeLabel)
  }

  // Mouse move handler for selection
  const handleMouseMove = (e: any) => {
    if (!e || !e.activeLabel || !refAreaLeft) return
    setRefAreaRight(e.activeLabel)
  }

  // Mouse up handler for selection
  const handleMouseUp = () => {
    if (!refAreaLeft || !refAreaRight) {
      setRefAreaLeft(null)
      setRefAreaRight(null)
      return
    }

    // Find indices for the selected area
    const leftIdx = formattedData.findIndex((item) => item.formattedTime === refAreaLeft)
    const rightIdx = formattedData.findIndex((item) => item.formattedTime === refAreaRight)

    // Ensure left is before right
    const startIdx = Math.min(leftIdx, rightIdx)
    const endIdx = Math.max(leftIdx, rightIdx)

    if (startIdx !== -1 && endIdx !== -1 && startIdx !== endIdx) {
      setLeftIndex(startIdx)
      setRightIndex(endIdx)
      setZoomedData(formattedData.slice(startIdx, endIdx + 1))
      setIsZoomed(true)
    }

    setRefAreaLeft(null)
    setRefAreaRight(null)
  }

  // Zoom in
  const zoomIn = () => {
    if (zoomedData.length <= 10) return // Prevent zooming in too far

    const midPoint = Math.floor(zoomedData.length / 2)
    const newStartIdx = Math.max(0, midPoint - Math.floor(zoomedData.length / 4))
    const newEndIdx = Math.min(zoomedData.length - 1, midPoint + Math.floor(zoomedData.length / 4))

    setZoomedData(zoomedData.slice(newStartIdx, newEndIdx + 1))
    setIsZoomed(true)
  }

  // Zoom out
  const zoomOut = () => {
    if (!isZoomed) return

    if (leftIndex === null || rightIndex === null) {
      resetZoom()
      return
    }

    // Calculate new indices that show more data
    const currentRange = rightIndex - leftIndex
    const newLeftIdx = Math.max(0, leftIndex - Math.floor(currentRange / 2))
    const newRightIdx = Math.min(formattedData.length - 1, rightIndex + Math.floor(currentRange / 2))

    // If we're showing almost all data, just reset
    if (newRightIdx - newLeftIdx >= formattedData.length * 0.9) {
      resetZoom()
      return
    }

    setLeftIndex(newLeftIdx)
    setRightIndex(newRightIdx)
    setZoomedData(formattedData.slice(newLeftIdx, newRightIdx + 1))
  }

  // Reset zoom
  const resetZoom = () => {
    setZoomedData(formattedData)
    setLeftIndex(null)
    setRightIndex(null)
    setIsZoomed(false)
  }

  // Determine tick interval based on data size
  const getTickInterval = () => {
    const dataLength = zoomedData.length

    if (dataLength <= 24) return 1 // Show every point for small datasets
    if (dataLength <= 48) return 2 // Every 2 hours for 2 days
    if (dataLength <= 168) return 6 // Every 6 hours for a week
    return 12 // Every 12 hours for larger datasets
  }

  // If no data is available, show a placeholder message
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-[300px] bg-gray-100 rounded-md">
        <p className="text-gray-500">Enter parameters and click Analyze to see temperature graph</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <div className="text-sm font-medium">
          {dayCount > 0 ? `Displaying data for ${dayCount} day${dayCount > 1 ? "s" : ""}` : "No date information"}
        </div>
        <div className="flex space-x-2">
          <button
            onClick={zoomIn}
            className="p-1 rounded bg-gray-100 hover:bg-gray-200"
            title="Zoom In"
            disabled={zoomedData.length <= 10}
          >
            <ZoomIn size={16} className={zoomedData.length <= 10 ? "text-gray-400" : ""} />
          </button>
          <button
            onClick={zoomOut}
            className="p-1 rounded bg-gray-100 hover:bg-gray-200"
            title="Zoom Out"
            disabled={!isZoomed}
          >
            <ZoomOut size={16} className={!isZoomed ? "text-gray-400" : ""} />
          </button>
          <button
            onClick={resetZoom}
            className="p-1 rounded bg-gray-100 hover:bg-gray-200"
            title="Reset Zoom"
            disabled={!isZoomed}
          >
            <RefreshCw size={16} className={!isZoomed ? "text-gray-400" : ""} />
          </button>
        </div>
      </div>

      <div className="h-[300px]" ref={chartRef}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={zoomedData}
            margin={{
              top: 5,
              right: 30,
              left: 20,
              bottom: 5,
            }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="formattedTime"
              interval={getTickInterval()}
              minTickGap={30}
              tick={{ fontSize: 12 }}
              angle={-30}
              textAnchor="end"
              height={60}
            />
            <YAxis
              label={{ value: "Temperature (°C)", angle: -90, position: "insideLeft", style: { textAnchor: "middle" } }}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload as TemperatureDataPoint & { formattedTime: string }
                  return (
                    <div className="bg-white p-2 border border-gray-200 rounded shadow-sm">
                      <div className="text-sm font-medium">{data.formattedTime}</div>
                      <div className="mt-1 text-sm">
                        <div className="font-bold text-blue-600">Internal: {data.Tin}°C</div>
                        <div className="font-bold text-red-500">External: {data.Tout}°C</div>
                      </div>
                    </div>
                  )
                }
                return null
              }}
            />
            {/* Reference line for 40°F (4.44°C) */}
            <ReferenceLine
              y={idealTemperatureCelsius}
              stroke="#16a34a"
              strokeDasharray="3 3"
              label={{
                value: "40°F (4.44°C)",
                position: "insideBottomRight",
                fill: "#16a34a",
                fontSize: 12,
              }}
            />
            {/* Reference area for selection */}
            {refAreaLeft && refAreaRight && (
              <ReferenceArea x1={refAreaLeft} x2={refAreaRight} strokeOpacity={0.3} fill="#8884d8" fillOpacity={0.3} />
            )}
            <Line
              type="monotone"
              dataKey="Tin"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={zoomedData.length < 50} // Only show dots when zoomed in enough
              activeDot={{ r: 6, strokeWidth: 0 }}
              name="Internal"
            />
            <Line
              type="monotone"
              dataKey="Tout"
              stroke="#ef4444"
              strokeWidth={2}
              dot={zoomedData.length < 50} // Only show dots when zoomed in enough
              activeDot={{ r: 6, strokeWidth: 0 }}
              name="External"
              connectNulls={false}
              isAnimationActive={true}
            />
            <Legend />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="text-xs text-gray-500 text-center">
        {isZoomed ? (
          <span>
            Showing {zoomedData.length} of {formattedData.length} data points.
            <button onClick={resetZoom} className="text-blue-500 hover:underline ml-1">
              Reset zoom
            </button>
          </span>
        ) : (
          <span>Tip: Drag on the chart to select a range to zoom in</span>
        )}
      </div>
    </div>
  )
}

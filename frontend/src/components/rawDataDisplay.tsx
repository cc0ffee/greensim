"use client"

import { useState } from "react"
import { Download } from "lucide-react"

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

interface RawDataDisplayProps {
  data: TemperatureDataPoint[]
}

export default function RawDataDisplay({ data }: RawDataDisplayProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const [rowsPerPage, setRowsPerPage] = useState(10)

  // Log the data to see what we're working with
  console.log("Raw data component received data:", data)

  // If no data is available, show a placeholder message
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-[300px] bg-gray-100 rounded-md">
        <p className="text-gray-500">Enter parameters and click Analyze to see raw data</p>
      </div>
    )
  }

  // Filter data based on search term - make case insensitive and more robust
  const filteredData = data.filter((item) => {
    const searchLower = searchTerm.toLowerCase()
    return (
      (item.datetime && item.datetime.toLowerCase().includes(searchLower)) ||
      (item.Tin !== undefined && item.Tin.toString().includes(searchTerm)) ||
      (item.Tout !== undefined && item.Tout.toString().includes(searchTerm))
    )
  })

  // Pagination
  const totalPages = Math.ceil(filteredData.length / rowsPerPage)
  const startIndex = (currentPage - 1) * rowsPerPage
  const paginatedData = filteredData.slice(startIndex, startIndex + rowsPerPage)

  // Function to download data as CSV
  const downloadCSV = () => {
    // Get all unique keys from the data
    const allKeys = Array.from(new Set(data.flatMap((item) => Object.keys(item))))

    const csvRows = [
      allKeys.join(","),
      ...data.map((item) =>
        allKeys
          .map((key) => {
            const value = (item as any)[key]
            // Wrap strings with commas in quotes
            return typeof value === "string" && value.includes(",") ? `"${value}"` : value
          })
          .join(","),
      ),
    ]

    const csvContent = csvRows.join("\n")
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)

    const link = document.createElement("a")
    link.setAttribute("href", url)
    link.setAttribute("download", `temperature_data_${new Date().toISOString().split("T")[0]}.csv`)
    link.style.visibility = "hidden"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Format date for display - make more robust
  const formatTimestamp = (timestamp: string) => {
    try {
      // Handle the specific format "YYYY-MM-DD HH:MM:SS"
      const date = new Date(timestamp.replace(" ", "T"))

      // Check if the date is valid
      if (isNaN(date.getTime())) {
        return timestamp // Return original if invalid
      }

      return date.toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch (error) {
      console.error("Error formatting timestamp:", error)
      return timestamp // Return original if error
    }
  }

  // Function to convert Celsius to Fahrenheit
  const celsiusToFahrenheit = (celsius: number): number => {
    return (celsius * 9) / 5 + 32
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <input
          type="text"
          placeholder="Search data..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 max-w-sm"
        />
        <button
          onClick={downloadCSV}
          className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-md bg-white hover:bg-gray-50 text-sm font-medium text-gray-700 shadow-sm transition-colors duration-200 ease-in-out"
        >
          <Download className="h-4 w-4 mr-2" />
          Export CSV
        </button>
      </div>

      <div className="border rounded-md overflow-auto max-h-[300px]">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Timestamp
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Internal Temp (Tin)
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                External Temp (Tout)
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedData.map((item, index) => {
              const internalTempF = celsiusToFahrenheit(item.Tin)
              const externalTempF = celsiusToFahrenheit(item.Tout)
              const isAboveIdeal = internalTempF >= 40

              return (
                <tr key={index} className={index % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatTimestamp(item.datetime)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {item.Tin.toFixed(1)}°C / {internalTempF.toFixed(1)}°F
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {item.Tout.toFixed(1)}°C / {externalTempF.toFixed(1)}°F
                  </td>
                  <td
                    className={`px-6 py-4 whitespace-nowrap text-sm ${isAboveIdeal ? "text-green-600" : "text-red-600"}`}
                  >
                    {isAboveIdeal ? "Above 40°F ✓" : "Below 40°F ✗"}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination controls */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-500">
          Showing {startIndex + 1}-{Math.min(startIndex + rowsPerPage, filteredData.length)} of {filteredData.length}{" "}
          records
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={rowsPerPage}
            onChange={(e) => {
              setRowsPerPage(Number(e.target.value))
              setCurrentPage(1) // Reset to first page when changing rows per page
            }}
            className="px-2 py-1 border border-gray-300 rounded text-sm"
          >
            <option value={10}>10 rows</option>
            <option value={25}>25 rows</option>
            <option value={50}>50 rows</option>
            <option value={100}>100 rows</option>
          </select>

          <div className="flex space-x-1">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50"
            >
              First
            </button>
            <button
              onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50"
            >
              Prev
            </button>
            <span className="px-2 py-1 text-sm">
              {currentPage} / {totalPages || 1}
            </span>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages || totalPages === 0}
              className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50"
            >
              Next
            </button>
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage === totalPages || totalPages === 0}
              className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50"
            >
              Last
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

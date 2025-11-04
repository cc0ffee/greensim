// Default to localhost:8080 if not set
// In Next.js, process.env is available on both client and server
// @ts-ignore - process.env is available in Next.js
export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080");

export async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

    const defaultHeaders = {
        "Content-Type": "application/json"
    }

    const response = await fetch(url, {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        }
    })

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`API Error (${response.status}): ${errorData.error || errorData.detail || response.statusText}`)
    }
    return await response.json()
}

// Submit a simulation job
export async function submitSimulation(params: {
    lat: number;
    lon: number;
    start_date: string;
    end_date: string;
    [key: string]: any;
}): Promise<{ job_id: string; status: string }> {
    return fetchAPI<{ job_id: string; status: string }>("/simulate", {
        method: "POST",
        body: JSON.stringify(params)
    });
}

// Get job status
export async function getJobStatus(jobId: string): Promise<{
    job_id: string;
    status: string;
    created_at?: string;
    updated_at?: string;
    error?: string;
}> {
    return fetchAPI(`/jobs/${jobId}`);
}

// Get job results (polls until done or error)
export async function getJobResults(jobId: string, maxWait: number = 60000): Promise<{
    job_id: string;
    status: string;
    result?: {
        job_id: string;
        data: any[];
        summary: any;
        params: any;
    };
}> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < maxWait) {
        const response = await fetchAPI<{
            job_id: string;
            status: string;
            result?: any;
        }>(`/results/${jobId}`);
        
        if (response.status === "done") {
            return response;
        } else if (response.status === "error") {
            throw new Error(`Job failed: ${response.status}`);
        }
        
        // Wait 2 seconds before polling again
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    throw new Error("Timeout waiting for job results");
}

// Convert city name to coordinates (simple lookup - you might want to use a geocoding API)
const CITY_COORDINATES: Record<string, { lat: number; lon: number }> = {
    "chicago": { lat: 41.8781, lon: -87.6298 },
    "new york": { lat: 40.7128, lon: -74.0060 },
    "los angeles": { lat: 34.0522, lon: -118.2437 },
    "houston": { lat: 29.7604, lon: -95.3698 },
    "phoenix": { lat: 33.4484, lon: -112.0740 },
    "philadelphia": { lat: 39.9526, lon: -75.1652 },
    "san antonio": { lat: 29.4241, lon: -98.4936 },
    "san diego": { lat: 32.7157, lon: -117.1611 },
    "dallas": { lat: 32.7767, lon: -96.7970 },
    "san jose": { lat: 37.3382, lon: -121.8863 },
};

export function getCityCoordinates(cityName: string): { lat: number; lon: number } | null {
    const normalized = cityName.toLowerCase().trim();
    return CITY_COORDINATES[normalized] || null;
}
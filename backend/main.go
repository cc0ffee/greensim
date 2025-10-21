package main

// backend/main.go
//
// Gin-based API that validates simulation parameters, enqueues jobs into Redis,
// and stores job metadata/results in Redis keys so workers can pick up and clients can query.

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

// JobStatus constants
const (
	StatusQueued  = "queued"
	StatusRunning = "running"
	StatusDone    = "done"
	StatusError   = "error"
)

// Redis keys / lists
const (
	RedisJobsList        = "simulation_jobs"        // list where full job JSON is pushed
	RedisResultsPrefix   = "job_result:"            // job_result:<jobID> -> JSON results (string)
	RedisJobMetaPrefix   = "job_meta:"              // job_meta:<jobID> -> JSON metadata
	RedisRecentJobsList  = "recent_simulation_ids"  // push job ids here for quick listing
	DefaultResultTTL     = 24 * time.Hour           // how long results persist in Redis by default
	RecentJobsMaxRetain  = 100                      // how many recent job IDs to keep in list
	RedisOpTimeout       = 5 * time.Second          // Redis operation timeout
	DefaultRedisAddr     = "redis:6379"             // default service name in docker-compose
	DefaultRedisDB       = 0
)

var (
	rdb     *redis.Client
	rdbAddr string
)

type SimulationParams struct {
	// physics params (snake_case in json expected)
	ThermalMass      *float64 `json:"thermal_mass,omitempty"`       // J/K (optional)
	ThermalMassKg    *float64 `json:"thermal_mass_kg,omitempty"`    // kg (optional)
	CpMass           *float64 `json:"cp_mass,omitempty"`            // J/kgK (optional, default water)
	VentilationRate  *float64 `json:"ventilation_rate,omitempty"`   // ACH or m3/s depending on your preference (we use ACH)
	U_day            *float64 `json:"U_day,omitempty"`
	U_night          *float64 `json:"U_night,omitempty"`
	A_glass          *float64 `json:"A_glass,omitempty"`
	tau_glass        *float64 `json:"tau_glass,omitempty"`
	ACH              *float64 `json:"ACH,omitempty"`
	Volume           *float64 `json:"V,omitempty"` // greenhouse volume (m3)
	C                *float64 `json:"C,omitempty"` // alternate direct C (J/K)
	T_init           *float64 `json:"T_init,omitempty"`
	Setpoint         *float64 `json:"setpoint,omitempty"`
	Lat              *float64 `json:"lat,omitempty"`
	Lon              *float64 `json:"lon,omitempty"`
	StartDate        string   `json:"start_date,omitempty"`
	EndDate          string   `json:"end_date,omitempty"`
	HeaterMaxW       *float64 `json:"heater_max_w,omitempty"`
	EvapRate         *float64 `json:"evap_rate,omitempty"`
	FractionSolarAir *float64 `json:"fraction_solar_to_air,omitempty"`
	// ... you can add more fields used by physics model
}

// Metadata stored in Redis for each job
type JobMeta struct {
	JobID     string           `json:"job_id"`
	Status    string           `json:"status"`
	CreatedAt time.Time        `json:"created_at"`
	UpdatedAt time.Time        `json:"updated_at"`
	Params    SimulationParams `json:"params"`
	Error     string           `json:"error,omitempty"`
	ResultKey string           `json:"result_key,omitempty"`
}

// job payload pushed to Redis (includes job id + params + created_at)
type JobPayload struct {
	JobID     string           `json:"job_id"`
	CreatedAt time.Time        `json:"created_at"`
	Params    SimulationParams `json:"params"`
}

func initRedis() {
	rdbAddr = os.Getenv("REDIS_ADDR")
	if rdbAddr == "" {
		rdbAddr = DefaultRedisAddr
	}
	rdb = redis.NewClient(&redis.Options{
		Addr: rdbAddr,
		DB:   DefaultRedisDB,
	})
	// quick ping
	ctx, cancel := context.WithTimeout(context.Background(), RedisOpTimeout)
	defer cancel()
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Fatalf("failed to connect to redis at %s: %v", rdbAddr, err)
	}
	log.Printf("connected to redis at %s", rdbAddr)
}

func main() {
	// read configuration from environment if needed
	initRedis()

	// Gin router
	router := gin.Default()

	// CORS for local frontend dev (adjust origins in production)
	router.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000", "http://127.0.0.1:3000"},
		AllowMethods:     []string{"GET", "POST", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	// Health
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	// Submit a job
	router.POST("/simulate", func(c *gin.Context) {
		var params SimulationParams
		if err := c.BindJSON(&params); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid JSON: " + err.Error()})
			return
		}

		// basic validation & defaults
		applyDefaults(&params)

		// create job id and payload
		jobID := uuid.NewString()
		now := time.Now().UTC()

		payload := JobPayload{
			JobID:     jobID,
			CreatedAt: now,
			Params:    params,
		}
		payloadBytes, err := json.Marshal(payload)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to marshal job payload"})
			return
		}

		// push payload into list (queue)
		ctx, cancel := context.WithTimeout(context.Background(), RedisOpTimeout)
		defer cancel()
		if err := rdb.RPush(ctx, RedisJobsList, payloadBytes).Err(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to enqueue job: " + err.Error()})
			return
		}

		// create job meta and store
		meta := JobMeta{
			JobID:     jobID,
			Status:    StatusQueued,
			CreatedAt: now,
			UpdatedAt: now,
			Params:    params,
			ResultKey: RedisResultsPrefix + jobID,
		}
		metaBytes, _ := json.Marshal(meta)
		if err := rdb.Set(ctx, RedisJobMetaPrefix+jobID, metaBytes, DefaultResultTTL).Err(); err != nil {
			// log but do not fail enqueue (best-effort)
			log.Printf("warning: failed to set job meta: %v", err)
		}

		// push job id into recent list (trim)
		if err := rdb.LPush(ctx, RedisRecentJobsList, jobID).Err(); err == nil {
			rdb.LTrim(ctx, RedisRecentJobsList, 0, RecentJobsMaxRetain-1)
		}

		c.JSON(http.StatusAccepted, gin.H{
			"job_id": jobID,
			"status": StatusQueued,
		})
	})

	// Get results for a job
	router.GET("/results/:job_id", func(c *gin.Context) {
		jobID := c.Param("job_id")
		ctx, cancel := context.WithTimeout(context.Background(), RedisOpTimeout)
		defer cancel()

		res, err := rdb.Get(ctx, RedisResultsPrefix+jobID).Result()
		if err == redis.Nil {
			// not ready
			// return status from job_meta if exists
			metaBytes, err2 := rdb.Get(ctx, RedisJobMetaPrefix+jobID).Result()
			if err2 == nil {
				var meta JobMeta
				_ = json.Unmarshal([]byte(metaBytes), &meta)
				c.JSON(http.StatusOK, gin.H{"job_id": jobID, "status": meta.Status})
				return
			}
			c.JSON(http.StatusNotFound, gin.H{"error": "no result or job not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "redis error: " + err.Error()})
			return
		}

		// return JSON result as-is (assuming worker stores JSON string)
		var parsed interface{}
		if err := json.Unmarshal([]byte(res), &parsed); err == nil {
			c.JSON(http.StatusOK, gin.H{"job_id": jobID, "status": StatusDone, "result": parsed})
			return
		}

		// fallback raw
		c.JSON(http.StatusOK, gin.H{"job_id": jobID, "status": StatusDone, "result": res})
	})

	// Get recent results (list of recent job ids)
	router.GET("/results", func(c *gin.Context) {
		ctx, cancel := context.WithTimeout(context.Background(), RedisOpTimeout)
		defer cancel()
		ids, err := rdb.LRange(ctx, RedisRecentJobsList, 0, 49).Result()
		if err != nil && err != redis.Nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "redis error: " + err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"recent_job_ids": ids})
	})

	// Get job metadata
	router.GET("/jobs/:job_id", func(c *gin.Context) {
		jobID := c.Param("job_id")
		ctx, cancel := context.WithTimeout(context.Background(), RedisOpTimeout)
		defer cancel()
		metaStr, err := rdb.Get(ctx, RedisJobMetaPrefix+jobID).Result()
		if err == redis.Nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "job not found"})
			return
		} else if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "redis error: " + err.Error()})
			return
		}
		var meta JobMeta
		if err := json.Unmarshal([]byte(metaStr), &meta); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to parse job meta"})
			return
		}
		c.JSON(http.StatusOK, meta)
	})

	// Start server
	addr := ":8080"
	if p := os.Getenv("PORT"); p != "" {
		addr = ":" + p
	}
	log.Printf("starting backend on %s", addr)
	if err := router.Run(addr); err != nil {
		log.Fatalf("failed to run server: %v", err)
	}
}

// applyDefaults sets reasonable defaults for missing fields
func applyDefaults(p *SimulationParams) {
	// defaults chosen to match your worker model defaults
	if p.A_glass == nil {
		def := 50.0
		p.A_glass = &def
	}
	if p.tau_glass == nil {
		def := 0.85
		p.tau_glass = &def
	}
	if p.U_day == nil {
		def := 3.0
		p.U_day = &def
	}
	if p.U_night == nil {
		def := 0.6
		p.U_night = &def
	}
	if p.ACH == nil {
		def := 0.5
		p.ACH = &def
	}
	if p.Volume == nil {
		def := 100.0
		p.Volume = &def
	}
	if p.C == nil && p.ThermalMassKg == nil {
		// default C equivalent (J/K)
		def := 2e7
		p.C = &def
	}
	if p.CpMass == nil {
		def := 4186.0
		p.CpMass = &def
	}
	if p.T_init == nil {
		def := 15.0
		p.T_init = &def
	}
	if p.Setpoint == nil {
		def := 12.0
		p.Setpoint = &def
	}
	if p.HeaterMaxW == nil {
		def := 5000.0
		p.HeaterMaxW = &def
	}
	if p.FractionSolarAir == nil {
		def := 0.5
		p.FractionSolarAir = &def
	}
	// lat/lon left nil if not provided
}

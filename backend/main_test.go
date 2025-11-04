package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Test helpers
func setupTestRedis() *redis.Client {
	client := redis.NewClient(&redis.Options{
		Addr: "localhost:6379",
		DB:   1, // Use different DB for tests
	})
	// Test connection
	ctx := context.Background()
	if err := client.Ping(ctx).Err(); err != nil {
		return nil // Redis not available
	}
	return client
}

func checkRedisAvailable(t *testing.T) bool {
	client := setupTestRedis()
	if client == nil {
		t.Skip("Redis not available")
		return false
	}
	return true
}

func setupRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	// Use test Redis
	testRdb := setupTestRedis()
	rdb = testRdb
	
	router := gin.Default()
	router.Use(func(c *gin.Context) {
		// Simple CORS for tests
		c.Header("Access-Control-Allow-Origin", "*")
		c.Next()
	})

	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	router.POST("/simulate", func(c *gin.Context) {
		var params SimulationParams
		if err := c.BindJSON(&params); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid JSON: " + err.Error()})
			return
		}
		applyDefaults(&params)
		jobID := "test-job-id"
		now := time.Now().UTC()
		payload := JobPayload{
			JobID:     jobID,
			CreatedAt: now,
			Params:    params,
		}
		payloadBytes, _ := json.Marshal(payload)
		ctx := c.Request.Context()
		rdb.RPush(ctx, RedisJobsList, payloadBytes)
		meta := JobMeta{
			JobID:     jobID,
			Status:    StatusQueued,
			CreatedAt: now,
			UpdatedAt: now,
			Params:    params,
			ResultKey: RedisResultsPrefix + jobID,
		}
		metaBytes, _ := json.Marshal(meta)
		rdb.Set(ctx, RedisJobMetaPrefix+jobID, metaBytes, DefaultResultTTL)
		c.JSON(http.StatusAccepted, gin.H{
			"job_id": jobID,
			"status": StatusQueued,
		})
	})

	router.GET("/results/:job_id", func(c *gin.Context) {
		jobID := c.Param("job_id")
		ctx := c.Request.Context()
		res, err := rdb.Get(ctx, RedisResultsPrefix+jobID).Result()
		if err == redis.Nil {
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
		var parsed interface{}
		if err := json.Unmarshal([]byte(res), &parsed); err == nil {
			c.JSON(http.StatusOK, gin.H{"job_id": jobID, "status": StatusDone, "result": parsed})
			return
		}
		c.JSON(http.StatusOK, gin.H{"job_id": jobID, "status": StatusDone, "result": res})
	})

	router.GET("/results", func(c *gin.Context) {
		ctx := c.Request.Context()
		ids, err := rdb.LRange(ctx, RedisRecentJobsList, 0, 49).Result()
		if err != nil && err != redis.Nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "redis error: " + err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"recent_job_ids": ids})
	})

	router.GET("/jobs/:job_id", func(c *gin.Context) {
		jobID := c.Param("job_id")
		ctx := c.Request.Context()
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

	return router
}

func TestHealthEndpoint(t *testing.T) {
	router := setupRouter()
	
	req, _ := http.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, "ok", response["status"])
}

func TestApplyDefaults(t *testing.T) {
	params := SimulationParams{}
	applyDefaults(&params)

	assert.NotNil(t, params.A_glass)
	assert.NotNil(t, params.TauGlass)
	assert.NotNil(t, params.U_day)
	assert.NotNil(t, params.U_night)
	assert.NotNil(t, params.ACH)
	assert.NotNil(t, params.Volume)
	assert.NotNil(t, params.T_init)
	assert.NotNil(t, params.Setpoint)
	assert.NotNil(t, params.HeaterMaxW)
	assert.NotNil(t, params.FractionSolarAir)

	assert.Equal(t, 50.0, *params.A_glass)
	assert.Equal(t, 0.85, *params.TauGlass)
	assert.Equal(t, 3.0, *params.U_day)
	assert.Equal(t, 0.6, *params.U_night)
	assert.Equal(t, 0.5, *params.ACH)
	assert.Equal(t, 100.0, *params.Volume)
	assert.Equal(t, 15.0, *params.T_init)
	assert.Equal(t, 12.0, *params.Setpoint)
	assert.Equal(t, 5000.0, *params.HeaterMaxW)
	assert.Equal(t, 0.5, *params.FractionSolarAir)
}

func TestApplyDefaultsPreservesExistingValues(t *testing.T) {
	customGlass := 75.0
	params := SimulationParams{
		A_glass: &customGlass,
	}
	applyDefaults(&params)

	assert.Equal(t, customGlass, *params.A_glass)
	assert.NotNil(t, params.U_day)
}

func TestSubmitJob(t *testing.T) {
	if !checkRedisAvailable(t) {
		return
	}
	router := setupRouter()
	ctx := context.Background()
	
	// Clear Redis
	rdb.FlushDB(ctx)

	params := SimulationParams{
		Lat:       floatPtr(41.8781),
		Lon:       floatPtr(-87.6298),
		StartDate: "2025-11-01",
		EndDate:   "2025-11-02",
	}

	jsonData, _ := json.Marshal(params)
	req, _ := http.NewRequest("POST", "/simulate", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusAccepted, w.Code)
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Contains(t, response, "job_id")
	assert.Equal(t, StatusQueued, response["status"])

	// Verify job was added to queue
	jobID := response["job_id"].(string)
	metaStr, err := rdb.Get(ctx, RedisJobMetaPrefix+jobID).Result()
	require.NoError(t, err)
	var meta JobMeta
	json.Unmarshal([]byte(metaStr), &meta)
	assert.Equal(t, StatusQueued, meta.Status)
}

func TestGetJobMeta(t *testing.T) {
	if !checkRedisAvailable(t) {
		return
	}
	router := setupRouter()
	ctx := context.Background()
	
	// Setup: create a job
	rdb.FlushDB(ctx)
	jobID := "test-job-123"
	meta := JobMeta{
		JobID:     jobID,
		Status:    StatusQueued,
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
		Params:    SimulationParams{},
	}
	metaBytes, _ := json.Marshal(meta)
	rdb.Set(ctx, RedisJobMetaPrefix+jobID, metaBytes, DefaultResultTTL)

	req, _ := http.NewRequest("GET", "/jobs/"+jobID, nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response JobMeta
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, jobID, response.JobID)
	assert.Equal(t, StatusQueued, response.Status)
}

func TestGetJobMetaNotFound(t *testing.T) {
	if !checkRedisAvailable(t) {
		return
	}
	router := setupRouter()
	ctx := context.Background()
	rdb.FlushDB(ctx)

	req, _ := http.NewRequest("GET", "/jobs/nonexistent", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestGetResults(t *testing.T) {
	if !checkRedisAvailable(t) {
		return
	}
	router := setupRouter()
	ctx := context.Background()
	
	// Setup: create a job with result
	rdb.FlushDB(ctx)
	jobID := "test-result-job"
	result := map[string]interface{}{
		"job_id": jobID,
		"data":   []map[string]interface{}{},
	}
	resultBytes, _ := json.Marshal(result)
	rdb.Set(ctx, RedisResultsPrefix+jobID, resultBytes, DefaultResultTTL)

	req, _ := http.NewRequest("GET", "/results/"+jobID, nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, StatusDone, response["status"])
	assert.Contains(t, response, "result")
}

func TestGetResultsQueued(t *testing.T) {
	if !checkRedisAvailable(t) {
		return
	}
	router := setupRouter()
	ctx := context.Background()
	
	// Setup: create a job without result (queued)
	rdb.FlushDB(ctx)
	jobID := "test-queued-job"
	meta := JobMeta{
		JobID:     jobID,
		Status:    StatusQueued,
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
	}
	metaBytes, _ := json.Marshal(meta)
	rdb.Set(ctx, RedisJobMetaPrefix+jobID, metaBytes, DefaultResultTTL)

	req, _ := http.NewRequest("GET", "/results/"+jobID, nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	assert.Equal(t, StatusQueued, response["status"])
}

func TestGetRecentJobs(t *testing.T) {
	if !checkRedisAvailable(t) {
		return
	}
	router := setupRouter()
	ctx := context.Background()
	
	// Setup: add some job IDs
	rdb.FlushDB(ctx)
	rdb.LPush(ctx, RedisRecentJobsList, "job1", "job2", "job3")

	req, _ := http.NewRequest("GET", "/results", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var response map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &response)
	ids := response["recent_job_ids"].([]interface{})
	assert.Greater(t, len(ids), 0)
}

// Helper function
func floatPtr(f float64) *float64 {
	return &f
}


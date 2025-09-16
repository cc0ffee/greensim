package main

import (
	"context"
	"encoding/json"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
)

type SimulationParams struct {
	ThermalMass     float64 `json:"thermal_mass"`
	VentilationRate float64 `json:"ventilation_rate"`
	U_day    		float64 `json:"U_day,omitempty"`
	U_night  		float64 `json:"U_night,omitempty"`
	A_glass  		float64 `json:"A_glass,omitempty"`
	C        		float64 `json:"C,omitempty"`
	T_init   		float64 `json:"T_init,omitempty"`
	Setpoint 		float64 `json:"setpoint,omitempty"`
	Lat      		float64 `json:"lat,omitempty"`
	Lon      		float64 `json:"lon,omitempty"`
	StartDate 		string `json:"start_date,omitempty"`
	EndDate   		string `json:"end_date,omitempty"`
}

func main() {

	var client = redis.NewClient(&redis.Options{
		Addr: "localhost:6379"
	})

	var ctx = context.Background()

	router := gin.Default()

	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})


	router.POST("/simulate", func(c *gin.Context) {
		var params SimulationParams
		if err := c.BindJSON(&params); err != mil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		data, err := json.Marshall(params)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to serialize job"})
			return
		}

		if err := rdb.RPush(ctx, "simulation_jobs", data).Err(); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to enqueue job"})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"message": "simulation job queued",
			"params":  params,
		})
	})

	router.GET("/results", func(c *gin.Context) {
		results, err := rdb.LRange(ctx, "simulation_results", 0, -1).Result()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"results": results})
	})

	router.Run("0.0.0.0:8080")
}

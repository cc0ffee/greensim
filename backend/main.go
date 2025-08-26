package main

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func main() {
	router := gin.Default()

	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	router.POST("/simulate", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"message": "simulation job received"})
	})

	router.Run("0.0.0.0:8080")
}

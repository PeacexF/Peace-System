package collectors

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"time"

	"peace-system/collectors/shared"

	"github.com/shirou/gopsutil/v3/cpu" // measure cpu
)

func GetCpu() {
	// Load config
	cfg, err := shared.LoadConfig("../settings/config.json")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	pipelineAddr := fmt.Sprintf("127.0.0.1:%d", cfg.PipelinePort)
	interval := time.Duration(cfg.Intervals.CPU) * time.Second

	// UDP connect
	conn, err := net.Dial("udp", pipelineAddr)
	if err != nil {
		log.Fatal("Could not connect to pipeline:", err)
	}
	defer conn.Close()

	fmt.Printf("CPU Collector started. Sending to %s\n", pipelineAddr)

	// The FOR loop in each collector is the actual info gathering and sending part, it is different in each collector.
	for {
		// collect cpu use
		percentages, err := cpu.Percent(time.Second, false)
		if err != nil {
			log.Printf("Error getting CPU percent: %v", err)
			continue
		}

		if len(percentages) > 0 {
			// make event
			event := shared.Event{
				Type:   "metric",
				Source: "cpu_collector",
				Data: map[string]interface{}{
					"cpu_usage_percent": percentages[0],
				},
				Timestamp: time.Now().Unix(),
			}

			// JSON
			jsonData, _ := json.Marshal(event)

			// send
			_, err := conn.Write(jsonData)
			if err != nil {
				log.Printf("Error sending data: %v", err)
			} else {
				log.Printf("Sent: %.2f%%", percentages[0])
			}
		}

		time.Sleep(interval)
	}
}

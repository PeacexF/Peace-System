package collectors

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"time"

	"peace-system/collectors/shared"

	"github.com/shirou/gopsutil/v3/mem"
)

// READ cpu.go FOR COMMENTED CODE, SCRUCTURE IS THE SAME

func GetRam() {
	cfg, err := shared.LoadConfig("../settings/config.json")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	pipelineAddr := fmt.Sprintf("127.0.0.1:%d", cfg.PipelinePort)
	interval := time.Duration(cfg.Intervals.RAM) * time.Second
	if interval == 0 {
		interval = 5 * time.Second
	}

	conn, err := net.Dial("udp", pipelineAddr)
	if err != nil {
		log.Fatal("Could not connect to pipeline:", err)
	}
	defer conn.Close()

	fmt.Printf("RAM Collector started. Sending to %s\n", pipelineAddr)

	for {
		v, err := mem.VirtualMemory()
		if err != nil {
			log.Printf("Error getting RAM metrics: %v", err)
			continue
		}

		event := shared.Event{
			Type:   "metric",
			Source: "ram_collector",
			Data: map[string]interface{}{
				"used_percent": v.UsedPercent,
				"available_mb": v.Available / 1024 / 1024, // конверт в МБ
				"total_mb":     v.Total / 1024 / 1024,
			},
			Timestamp: time.Now().Unix(),
		}

		jsonData, _ := json.Marshal(event)
		_, err = conn.Write(jsonData)

		if err != nil {
			log.Printf("Error sending RAM data: %v", err)
		} else {
			log.Printf("Sent RAM: %.2f%% used", v.UsedPercent)
		}

		time.Sleep(interval)
	}
}

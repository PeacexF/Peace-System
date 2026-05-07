package collectors

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"time"

	"peace-system/collectors/shared"

	"github.com/shirou/gopsutil/v3/disk"
)

// READ cpu.go FOR COMMENTED CODE, SCRUCTURE IS THE SAME

func GetDisk() {
	cfg, err := shared.LoadConfig("../settings/config.json")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	pipelineAddr := fmt.Sprintf("127.0.0.1:%d", cfg.PipelinePort)
	interval := time.Duration(cfg.Intervals.DISK) * time.Second
	if interval == 0 {
		interval = 60 * time.Second
	}

	conn, err := net.Dial("udp", pipelineAddr)
	if err != nil {
		log.Fatal("Could not connect to pipeline:", err)
	}
	defer conn.Close()

	fmt.Printf("Disk Collector started. Sending to %s\n", pipelineAddr)

	for {
		// надо подумать как адаптировать под разные ОС
		usage, err := disk.Usage("/")
		if err != nil {
			log.Printf("Error getting disk usage: %v", err)
			continue
		}

		event := shared.Event{
			Type:   "metric",
			Source: "disk_collector",
			Data: map[string]interface{}{
				"used_percent": usage.UsedPercent,
				"free_gb":      usage.Free / 1024 / 1024 / 1024,
				"total_gb":     usage.Total / 1024 / 1024 / 1024,
				"path":         usage.Path,
			},
			Timestamp: time.Now().Unix(),
		}

		jsonData, _ := json.Marshal(event)

		_, err = conn.Write(jsonData)
		if err != nil {
			log.Printf("Error sending disk data: %v", err)
		} else {
			log.Printf("Sent Disk: %.2f%% used on %s", usage.UsedPercent, usage.Path)
		}

		time.Sleep(interval)
	}
}

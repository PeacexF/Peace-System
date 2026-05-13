package collectors

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"time"

	"peace-system/collectors/shared"

	psNet "github.com/shirou/gopsutil/v3/net"
)

// READ cpu.go FOR COMMENTED CODE, SCRUCTURE IS THE SAME

func GetNetwork() {
	cfg, err := shared.LoadConfig("../settings/config.json")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	pipelineAddr := fmt.Sprintf("127.0.0.1:%d", cfg.PipelinePort)
	interval := time.Duration(cfg.Intervals.NETWORK) * time.Second
	if interval == 0 {
		interval = 10 * time.Second
	}

	conn, err := net.Dial("udp", pipelineAddr)
	if err != nil {
		log.Fatal("Could not connect to pipeline:", err)
	}
	defer conn.Close()

	fmt.Printf("Network Collector started. Sending to %s\n", pipelineAddr)

	for {
		ioStats, err := psNet.IOCounters(false)
		if err != nil {
			log.Printf("Error getting net IO: %v", err)
			continue
		}

		// список портов
		connections, err := psNet.Connections("all")
		if err != nil {
			log.Printf("Error getting connections: %v", err)
			continue
		}

		activePorts := make([]map[string]interface{}, 0)
		for _, c := range connections {
			if c.Status == "LISTEN" || c.Status == "ESTABLISHED" {
				activePorts = append(activePorts, map[string]interface{}{
					"local_port":  c.Laddr.Port,
					"remote_addr": c.Raddr.IP,
					"status":      c.Status,
					"family":      c.Family,
				})
			}
		}

		event := shared.Event{
			Type:   "metric",
			Source: "network_collector",
			Data: map[string]interface{}{
				"bytes_sent":         ioStats[0].BytesSent,
				"bytes_recv":         ioStats[0].BytesRecv,
				"active_ports":       activePorts,
				"network_conn_count": len(activePorts),
			},
			Timestamp: time.Now().Unix(),
		}

		jsonData, _ := json.Marshal(event)
		_, err = conn.Write(jsonData)

		if err != nil {
			log.Printf("Error sending net data: %v", err)
		} else {
			log.Printf("Sent Network info: %d active connections", len(activePorts))
		}

		time.Sleep(interval)
	}
}

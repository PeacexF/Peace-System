package collectors

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"time"

	"peace-system/collectors/shared"

	"github.com/docker/docker/api/types/container"
	"github.com/docker/docker/api/types/image"
	"github.com/docker/docker/api/types/network"
	"github.com/docker/docker/client"
)

// READ cpu.go FOR COMMENTED CODE, SCRUCTURE IS THE SAME

func GetDocker() {
	cfg, err := shared.LoadConfig("../settings/config.json")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	pipelineAddr := fmt.Sprintf("127.0.0.1:%d", cfg.PipelinePort)
	interval := time.Duration(cfg.Intervals.DOCKER) * time.Second
	if interval == 0 {
		interval = 30 * time.Second
	}

	conn, err := net.Dial("udp", pipelineAddr)
	if err != nil {
		log.Fatal("Could not connect to pipeline:", err)
	}
	defer conn.Close()

	// Docker клиент
	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		log.Printf("Docker Client Error: %v", err)
		return
	}
	defer cli.Close()

	fmt.Printf("Docker Collector started. Sending to %s\n", pipelineAddr)

	for {
		ctx := context.Background()

		// список активных контейнеров
		containers, err := cli.ContainerList(ctx, container.ListOptions{All: false})
		if err != nil {
			log.Printf("Error listing containers: %v", err)
		}

		containerData := make([]map[string]interface{}, 0)
		for _, c := range containers {
			containerData = append(containerData, map[string]interface{}{
				"id":     c.ID[:12],
				"name":   c.Names[0],
				"image":  c.Image,
				"state":  c.State,
				"status": c.Status,
			})
		}

		// список образов
		images, err := cli.ImageList(ctx, image.ListOptions{})
		if err != nil {
			log.Printf("Error listing images: %v", err)
		}

		// cписок сетей
		networks, err := cli.NetworkList(ctx, network.ListOptions{})
		if err != nil {
			log.Printf("Error listing networks: %v", err)
		}

		netData := make([]string, 0)
		for _, n := range networks {
			netData = append(netData, n.Name)
		}

		event := shared.Event{
			Type:   "metric",
			Source: "docker_collector",
			Data: map[string]interface{}{
				"active_containers_count": len(containers),
				"containers":              containerData,
				"total_images":            len(images),
				"networks":                netData,
			},
			Timestamp: time.Now().Unix(),
		}

		jsonData, _ := json.Marshal(event)
		_, err = conn.Write(jsonData)

		if err != nil {
			log.Printf("Error sending docker data: %v", err)
		} else {
			log.Printf("Sent Docker info: %d containers active", len(containers))
		}

		time.Sleep(interval)
	}
}

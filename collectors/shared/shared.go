package shared

import (
	"encoding/json"
	"os"
)

type Event struct {
	Type      string                 `json:"type"`
	Source    string                 `json:"source"`
	Data      map[string]interface{} `json:"data"`
	Timestamp int64                  `json:"timestamp"`
}

type Config struct {
	PipelinePort int `json:"pipeline_port"`
	Intervals    struct {
		RAM     int `json:"ram"`
		CPU     int `json:"cpu"`
		DISK    int `json:"disk"`
		DOCKER  int `json:"docker"`
		NETWORK int `json:"network"`
	} `json:"collection_intervals"`
}

func LoadConfig(path string) (*Config, error) {
	file, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cfg Config
	if err := json.Unmarshal(file, &cfg); err != nil {
		return nil, err
	}

	return &cfg, err
}

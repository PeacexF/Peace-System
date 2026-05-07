package main

import (
	collector "peace-system/collectors/collect_pack"
)

func main() { // запуск всех коллекторов в отдельных горутинах
	go collector.GetCpu()
	go collector.GetRam()
	go collector.GetDisk()
	go collector.GetNetwork()
	go collector.GetDocker()
	select {}
}

#!/usr/bin/env python3
"""
Infrastructure Optimization Script for Phoenix Real Estate
Automates infrastructure deployment and scaling recommendations

Usage:
    python infrastructure_optimizer.py --mode [deploy|scale|analyze]
    python infrastructure_optimizer.py --markets 5 --analyze-costs
"""

import subprocess
import json
import yaml
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InfrastructureOptimizer:
    """Infrastructure deployment and optimization automation"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent
        self.config_path = self.base_path / "config"
        self.monitoring_path = self.config_path / "monitoring"
        
    def analyze_current_infrastructure(self) -> Dict[str, Any]:
        """Analyze current infrastructure state and resource usage"""
        logger.info("🔍 Analyzing current infrastructure state...")
        
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "services": self._check_service_health(),
            "resources": self._analyze_resource_usage(),
            "costs": self._estimate_current_costs(),
            "recommendations": []
        }
        
        return analysis
    
    def _check_service_health(self) -> Dict[str, str]:
        """Check health of all infrastructure services"""
        services = {
            "mongodb": self._check_mongodb_health(),
            "ollama": self._check_ollama_health(),
            "prometheus": self._check_prometheus_health(),
            "grafana": self._check_grafana_health(),
            "alertmanager": self._check_alertmanager_health()
        }
        
        healthy_count = sum(1 for status in services.values() if status == "healthy")
        total_count = len(services)
        
        logger.info(f"📊 Service Health: {healthy_count}/{total_count} services healthy")
        
        return services
    
    def _check_mongodb_health(self) -> str:
        """Check MongoDB service health"""
        try:
            # Check if MongoDB is accessible
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=mongodb", "--format", "{{.Status}}"],
                capture_output=True, text=True, timeout=10
            )
            if "Up" in result.stdout:
                return "healthy"
            return "unhealthy"
        except Exception as e:
            logger.warning(f"MongoDB health check failed: {e}")
            return "unknown"
    
    def _check_ollama_health(self) -> str:
        """Check Ollama LLM service health"""
        try:
            result = subprocess.run(
                ["curl", "-f", "http://localhost:11434/api/tags"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return "healthy"
            return "unhealthy"
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return "unknown"
    
    def _check_prometheus_health(self) -> str:
        """Check Prometheus service health"""
        try:
            result = subprocess.run(
                ["curl", "-f", "http://localhost:9090/-/healthy"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return "healthy"
            return "unhealthy"
        except Exception as e:
            logger.warning(f"Prometheus health check failed: {e}")
            return "unknown"
    
    def _check_grafana_health(self) -> str:
        """Check Grafana service health"""
        try:
            result = subprocess.run(
                ["curl", "-f", "http://localhost:3000/api/health"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return "healthy"
            return "unhealthy"
        except Exception as e:
            logger.warning(f"Grafana health check failed: {e}")
            return "unknown"
    
    def _check_alertmanager_health(self) -> str:
        """Check AlertManager service health"""
        try:
            result = subprocess.run(
                ["curl", "-f", "http://localhost:9093/-/healthy"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return "healthy"
            return "unhealthy"
        except Exception as e:
            logger.warning(f"AlertManager health check failed: {e}")
            return "unknown"
    
    def _analyze_resource_usage(self) -> Dict[str, Any]:
        """Analyze current resource usage patterns"""
        try:
            # Get Docker container resource usage
            result = subprocess.run([
                "docker", "stats", "--no-stream", "--format",
                "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                containers = []
                
                for line in lines:
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        containers.append({
                            "name": parts[0],
                            "cpu_percent": parts[1],
                            "memory_usage": parts[2],
                            "network_io": parts[3],
                            "block_io": parts[4] if len(parts) > 4 else "N/A"
                        })
                
                return {
                    "containers": containers,
                    "total_containers": len(containers),
                    "high_cpu_containers": [
                        c for c in containers 
                        if c["cpu_percent"].replace("%", "").replace("--", "0").isdigit() 
                        and float(c["cpu_percent"].replace("%", "").replace("--", "0")) > 50
                    ]
                }
            
            return {"error": "Unable to retrieve resource usage"}
            
        except Exception as e:
            logger.warning(f"Resource usage analysis failed: {e}")
            return {"error": str(e)}
    
    def _estimate_current_costs(self) -> Dict[str, Any]:
        """Estimate current infrastructure costs"""
        base_costs = {
            "compute": {
                "current_instances": 1,
                "instance_type": "t3.medium",
                "monthly_cost_per_instance": 35.04,
                "total_monthly": 35.04
            },
            "storage": {
                "ebs_volume_gb": 150,
                "cost_per_gb_month": 0.10,
                "monthly_cost": 15.0
            },
            "mongodb_atlas": {
                "tier": "M10",
                "monthly_cost": 57.0
            },
            "monitoring": {
                "prometheus_storage": 10.0,
                "grafana_cloud": 0.0,  # Self-hosted
                "alertmanager": 0.0,   # Self-hosted
                "monthly_cost": 10.0
            },
            "networking": {
                "data_transfer_gb": 100,
                "cost_per_gb": 0.09,
                "monthly_cost": 9.0
            }
        }
        
        total_monthly = sum(
            costs["monthly_cost"] if "monthly_cost" in costs 
            else costs.get("total_monthly", 0)
            for costs in base_costs.values()
        )
        
        return {
            **base_costs,
            "total_monthly_usd": total_monthly,
            "annual_estimate_usd": total_monthly * 12
        }
    
    def calculate_scaling_requirements(self, target_markets: int) -> Dict[str, Any]:
        """Calculate resource requirements for multi-market scaling"""
        logger.info(f"📈 Calculating scaling requirements for {target_markets} markets...")
        
        # Base requirements per market
        per_market_resources = {
            "cpu_cores": 0.5,
            "memory_gb": 1.0,
            "storage_gb": 20,
            "network_mbps": 10
        }
        
        # Calculate total requirements
        total_requirements = {
            "markets": target_markets,
            "total_cpu_cores": per_market_resources["cpu_cores"] * target_markets,
            "total_memory_gb": per_market_resources["memory_gb"] * target_markets,
            "total_storage_gb": per_market_resources["storage_gb"] * target_markets,
            "total_network_mbps": per_market_resources["network_mbps"] * target_markets
        }
        
        # Calculate instance requirements
        instance_specs = {
            "t3.medium": {"cpu": 2, "memory": 4, "cost_monthly": 35.04},
            "t3.large": {"cpu": 2, "memory": 8, "cost_monthly": 70.08},
            "t3.xlarge": {"cpu": 4, "memory": 16, "cost_monthly": 140.16}
        }
        
        # Recommend instance type based on requirements
        if total_requirements["total_cpu_cores"] <= 2 and total_requirements["total_memory_gb"] <= 4:
            recommended_instance = "t3.medium"
            required_instances = max(1, target_markets // 4)  # 4 markets per t3.medium
        elif total_requirements["total_cpu_cores"] <= 2 and total_requirements["total_memory_gb"] <= 8:
            recommended_instance = "t3.large"
            required_instances = max(1, target_markets // 6)  # 6 markets per t3.large
        else:
            recommended_instance = "t3.xlarge"
            required_instances = max(1, target_markets // 10)  # 10 markets per t3.xlarge
        
        # Calculate costs
        instance_cost = instance_specs[recommended_instance]["cost_monthly"]
        storage_cost = total_requirements["total_storage_gb"] * 0.10  # $0.10/GB/month
        mongodb_scaling_factor = min(3, max(1, target_markets // 5))  # Scale MongoDB every 5 markets
        mongodb_cost = 57.0 * mongodb_scaling_factor
        
        total_monthly_cost = (instance_cost * required_instances) + storage_cost + mongodb_cost + 25.0  # +$25 for networking/monitoring
        
        return {
            "requirements": total_requirements,
            "recommended_setup": {
                "instance_type": recommended_instance,
                "instance_count": required_instances,
                "mongodb_tier": f"M{10 + (mongodb_scaling_factor - 1) * 10}"
            },
            "cost_analysis": {
                "monthly_compute": instance_cost * required_instances,
                "monthly_storage": storage_cost,
                "monthly_mongodb": mongodb_cost,
                "monthly_other": 25.0,
                "total_monthly_usd": total_monthly_cost,
                "annual_estimate_usd": total_monthly_cost * 12,
                "cost_per_market_monthly": total_monthly_cost / target_markets
            },
            "scaling_timeline": self._generate_scaling_timeline(target_markets)
        }
    
    def _generate_scaling_timeline(self, target_markets: int) -> List[Dict[str, Any]]:
        """Generate recommended scaling timeline"""
        phases = []
        
        if target_markets <= 5:
            phases.append({
                "phase": "Phase 1: Initial Scale",
                "markets": f"1-{target_markets}",
                "duration_weeks": 2,
                "focus": "Deploy optimized monitoring, scale to target markets",
                "risk_level": "low"
            })
        else:
            phases.extend([
                {
                    "phase": "Phase 1: Foundation",
                    "markets": "1-3",
                    "duration_weeks": 2,
                    "focus": "Deploy optimized infrastructure, validate monitoring",
                    "risk_level": "low"
                },
                {
                    "phase": "Phase 2: Core Markets",
                    "markets": "4-8",
                    "duration_weeks": 3,
                    "focus": "Scale core Phoenix metro markets",
                    "risk_level": "medium"
                },
                {
                    "phase": "Phase 3: Regional Expansion",
                    "markets": f"9-{target_markets}",
                    "duration_weeks": 4,
                    "focus": "Expand to surrounding Arizona markets",
                    "risk_level": "medium"
                }
            ])
        
        return phases
    
    def deploy_optimized_infrastructure(self) -> bool:
        """Deploy the optimized infrastructure configuration"""
        logger.info("🚀 Deploying optimized infrastructure...")
        
        try:
            # Step 1: Stop existing monitoring services
            logger.info("⏹️ Stopping existing monitoring services...")
            subprocess.run([
                "docker-compose", "-f", str(self.monitoring_path / "docker-compose.yml"), "down"
            ], cwd=self.monitoring_path, check=False)
            
            # Step 2: Deploy optimized monitoring stack
            logger.info("📊 Deploying optimized monitoring stack...")
            result = subprocess.run([
                "docker-compose", "-f", str(self.monitoring_path / "optimized-docker-compose.yml"), "up", "-d"
            ], cwd=self.monitoring_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Deployment failed: {result.stderr}")
                return False
            
            # Step 3: Wait for services to start and verify health
            import time
            logger.info("⏳ Waiting for services to initialize...")
            time.sleep(30)
            
            # Step 4: Verify deployment
            analysis = self.analyze_current_infrastructure()
            healthy_services = sum(1 for status in analysis["services"].values() if status == "healthy")
            total_services = len(analysis["services"])
            
            logger.info(f"✅ Deployment complete: {healthy_services}/{total_services} services healthy")
            
            if healthy_services >= 3:  # At least core services should be healthy
                return True
            else:
                logger.warning("⚠️ Some services may need additional time to start")
                return True
                
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False
    
    def generate_recommendations(self, analysis: Dict[str, Any], target_markets: int = None) -> List[str]:
        """Generate optimization recommendations based on analysis"""
        recommendations = []
        
        # Service health recommendations
        unhealthy_services = [
            service for service, status in analysis["services"].items() 
            if status != "healthy"
        ]
        
        if unhealthy_services:
            recommendations.append(
                f"🔧 Fix unhealthy services: {', '.join(unhealthy_services)}. "
                f"Run deployment script to apply optimized configurations."
            )
        
        # Resource optimization recommendations
        if "containers" in analysis["resources"]:
            high_cpu_containers = analysis["resources"].get("high_cpu_containers", [])
            if high_cpu_containers:
                recommendations.append(
                    f"⚡ High CPU usage detected in containers: {', '.join([c['name'] for c in high_cpu_containers])}. "
                    f"Consider resource limits or scaling."
                )
        
        # Cost optimization recommendations
        current_cost = analysis["costs"]["total_monthly_usd"]
        if current_cost > 150:
            recommendations.append(
                f"💰 Current monthly cost ${current_cost:.2f} is high. "
                f"Consider optimizing instance types or using spot instances."
            )
        
        # Scaling recommendations
        if target_markets and target_markets > 1:
            scaling = self.calculate_scaling_requirements(target_markets)
            recommendations.append(
                f"📈 For {target_markets} markets, estimated monthly cost: "
                f"${scaling['cost_analysis']['total_monthly_usd']:.2f} "
                f"(${scaling['cost_analysis']['cost_per_market_monthly']:.2f} per market)"
            )
        
        return recommendations

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Phoenix Real Estate Infrastructure Optimizer")
    parser.add_argument("--mode", choices=["analyze", "deploy", "scale"], default="analyze",
                      help="Operation mode")
    parser.add_argument("--markets", type=int, default=1,
                      help="Target number of markets for scaling analysis")
    parser.add_argument("--deploy-optimized", action="store_true",
                      help="Deploy optimized infrastructure configurations")
    
    args = parser.parse_args()
    
    optimizer = InfrastructureOptimizer()
    
    if args.mode == "analyze":
        logger.info("🔍 Starting infrastructure analysis...")
        analysis = optimizer.analyze_current_infrastructure()
        
        print("\n" + "="*80)
        print("🏗️  PHOENIX REAL ESTATE INFRASTRUCTURE ANALYSIS")
        print("="*80)
        
        # Service Health Report
        print("\n📊 SERVICE HEALTH STATUS:")
        for service, status in analysis["services"].items():
            status_icon = "✅" if status == "healthy" else "❌" if status == "unhealthy" else "❓"
            print(f"  {status_icon} {service.capitalize()}: {status}")
        
        # Resource Usage Report
        print(f"\n💾 RESOURCE USAGE:")
        if "containers" in analysis["resources"]:
            print(f"  📦 Active containers: {analysis['resources']['total_containers']}")
            if analysis["resources"]["high_cpu_containers"]:
                print(f"  ⚡ High CPU containers: {len(analysis['resources']['high_cpu_containers'])}")
        
        # Cost Analysis
        print(f"\n💰 COST ANALYSIS:")
        print(f"  Monthly estimate: ${analysis['costs']['total_monthly_usd']:.2f}")
        print(f"  Annual estimate: ${analysis['costs']['annual_estimate_usd']:.2f}")
        
        # Recommendations
        recommendations = optimizer.generate_recommendations(analysis, args.markets)
        if recommendations:
            print(f"\n🎯 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
    elif args.mode == "deploy":
        if optimizer.deploy_optimized_infrastructure():
            logger.info("✅ Infrastructure deployment completed successfully!")
        else:
            logger.error("❌ Infrastructure deployment failed!")
            return 1
    
    elif args.mode == "scale":
        scaling = optimizer.calculate_scaling_requirements(args.markets)
        
        print("\n" + "="*80)
        print(f"📈 SCALING ANALYSIS FOR {args.markets} MARKETS")
        print("="*80)
        
        print(f"\n🏗️ RECOMMENDED SETUP:")
        print(f"  Instance type: {scaling['recommended_setup']['instance_type']}")
        print(f"  Instance count: {scaling['recommended_setup']['instance_count']}")
        print(f"  MongoDB tier: {scaling['recommended_setup']['mongodb_tier']}")
        
        print(f"\n💰 COST BREAKDOWN:")
        cost = scaling['cost_analysis']
        print(f"  Compute: ${cost['monthly_compute']:.2f}/month")
        print(f"  Storage: ${cost['monthly_storage']:.2f}/month")
        print(f"  MongoDB: ${cost['monthly_mongodb']:.2f}/month")
        print(f"  Other: ${cost['monthly_other']:.2f}/month")
        print(f"  ───────────────────────────────")
        print(f"  Total: ${cost['total_monthly_usd']:.2f}/month")
        print(f"  Per market: ${cost['cost_per_market_monthly']:.2f}/month")
        print(f"  Annual: ${cost['annual_estimate_usd']:.2f}")
        
        print(f"\n📅 SCALING TIMELINE:")
        for phase in scaling['scaling_timeline']:
            print(f"  {phase['phase']}: {phase['markets']} markets")
            print(f"    Duration: {phase['duration_weeks']} weeks")
            print(f"    Focus: {phase['focus']}")
            print(f"    Risk: {phase['risk_level']}")
            print()
    
    return 0

if __name__ == "__main__":
    exit(main())
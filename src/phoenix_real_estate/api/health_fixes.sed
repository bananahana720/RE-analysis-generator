# Fix line 97 - replace incorrect database access
97c            count = 0            try:                async with self.db_client.get_database() as db:                    properties_collection = db["properties"]                    count = await properties_collection.count_documents({})            except Exception as e:                logger.warning(f"Could not count documents: {e}")                count = -1

# Fix ollama temperature access (line 145)
145s/self.ollama_client.temperature/"temperature": 0.1,  # Static value/

# Fix ollama timeout access (line 146) 
146s/self.ollama_client.timeout/"timeout_seconds": self.ollama_client.timeout_seconds/

# Fix ollama _generate call (line 152)
152s/await self.ollama_client._generate("Test", max_tokens=10)/await self.ollama_client.generate_completion("Test prompt", max_tokens=10)/

# Remove circuit breaker section (lines 164-169)
164,169d

# Fix connection pool attributes (lines 106-107)
106s/getattr(self.db_client, "active_connections", 0)/"max_size": getattr(self.db_client, "max_pool_size", 0)/
107s/getattr(self.db_client, "available_connections", 0)/"min_size": getattr(self.db_client, "min_pool_size", 0)/

# Add return type annotation for _add_health_record (line 46)
46s/def _add_health_record(self, component: str, healthy: bool, details: str):/def _add_health_record(self, component: str, healthy: bool, details: str) -> None:/

# Fix result initialization for component_health_handler
/try:/a        # Initialize result to avoid unbound variable error        result: Dict[str, Any] = {"status": "error", "error": "Unknown component"}
EOF < /dev/null

// Target: Neo4j 5.x Community-compatible node uniqueness syntax.
// Each imported node must carry its declared label. Required fields are checked offline.

CREATE CONSTRAINT kg_user_uid_unique IF NOT EXISTS
FOR (n:User) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT kg_host_uid_unique IF NOT EXISTS
FOR (n:Host) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT kg_ipaddress_uid_unique IF NOT EXISTS
FOR (n:IPAddress) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT kg_alert_uid_unique IF NOT EXISTS
FOR (n:Alert) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT kg_vulnerability_uid_unique IF NOT EXISTS
FOR (n:Vulnerability) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT kg_malware_uid_unique IF NOT EXISTS
FOR (n:Malware) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT kg_attacktechnique_uid_unique IF NOT EXISTS
FOR (n:AttackTechnique) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT kg_threatindicator_uid_unique IF NOT EXISTS
FOR (n:ThreatIndicator) REQUIRE n.uid IS UNIQUE;

CREATE CONSTRAINT kg_sourcerecord_uid_unique IF NOT EXISTS
FOR (n:SourceRecord) REQUIRE n.uid IS UNIQUE;

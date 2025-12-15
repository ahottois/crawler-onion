"""
Module de correlation d'entites.
Graphe de connaissances et scoring de correlation.
"""

import json
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from .logger import Log


@dataclass
class EntityNode:
    """Noeud d'entite dans le graphe."""
    id: str
    type: str  # email, domain, wallet, ip, username, phone
    value: str
    first_seen: str = ""
    last_seen: str = ""
    occurrence_count: int = 1
    source_domains: Set[str] = field(default_factory=set)
    source_urls: Set[str] = field(default_factory=set)
    metadata: Dict = field(default_factory=dict)
    risk_score: float = 0.0
    tags: Set[str] = field(default_factory=set)


@dataclass
class EntityEdge:
    """Lien entre deux entites."""
    source_id: str
    target_id: str
    relationship: str  # co-occurrence, same_domain, same_page, linked
    weight: float = 1.0
    first_seen: str = ""
    last_seen: str = ""
    occurrence_count: int = 1
    evidence: List[str] = field(default_factory=list)


@dataclass
class CorrelationResult:
    """Resultat de correlation."""
    entity1_id: str
    entity2_id: str
    correlation_score: float
    confidence: float
    relationship_type: str
    evidence: List[str] = field(default_factory=list)
    interpretation: str = ""


class EntityGraph:
    """Graphe d'entites pour correlation."""
    
    def __init__(self):
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: Dict[str, EntityEdge] = {}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)  # node_id -> connected node_ids
        self.type_index: Dict[str, Set[str]] = defaultdict(set)  # type -> node_ids
        self.domain_index: Dict[str, Set[str]] = defaultdict(set)  # domain -> node_ids
    
    def _generate_node_id(self, entity_type: str, value: str) -> str:
        """Genere un ID unique pour un noeud."""
        return f"{entity_type}:{value.lower()}"
    
    def _generate_edge_id(self, source_id: str, target_id: str) -> str:
        """Genere un ID unique pour un lien."""
        # Ordre alphabetique pour consistance
        if source_id > target_id:
            source_id, target_id = target_id, source_id
        return f"{source_id}--{target_id}"
    
    def add_entity(self, entity_type: str, value: str, 
                   source_domain: str = "", source_url: str = "",
                   metadata: Dict = None) -> str:
        """Ajoute une entite au graphe."""
        node_id = self._generate_node_id(entity_type, value)
        now = datetime.utcnow().isoformat()
        
        if node_id in self.nodes:
            # Mise a jour
            node = self.nodes[node_id]
            node.occurrence_count += 1
            node.last_seen = now
            if source_domain:
                node.source_domains.add(source_domain)
            if source_url:
                node.source_urls.add(source_url)
            if metadata:
                node.metadata.update(metadata)
        else:
            # Nouveau noeud
            node = EntityNode(
                id=node_id,
                type=entity_type,
                value=value,
                first_seen=now,
                last_seen=now,
                source_domains={source_domain} if source_domain else set(),
                source_urls={source_url} if source_url else set(),
                metadata=metadata or {}
            )
            self.nodes[node_id] = node
            self.type_index[entity_type].add(node_id)
        
        if source_domain:
            self.domain_index[source_domain].add(node_id)
        
        return node_id
    
    def add_relationship(self, source_id: str, target_id: str,
                        relationship: str = "co-occurrence",
                        evidence: str = "") -> str:
        """Ajoute un lien entre deux entites."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return ""
        
        edge_id = self._generate_edge_id(source_id, target_id)
        now = datetime.utcnow().isoformat()
        
        if edge_id in self.edges:
            edge = self.edges[edge_id]
            edge.occurrence_count += 1
            edge.weight += 0.1
            edge.last_seen = now
            if evidence:
                edge.evidence.append(evidence)
        else:
            edge = EntityEdge(
                source_id=source_id,
                target_id=target_id,
                relationship=relationship,
                first_seen=now,
                last_seen=now,
                evidence=[evidence] if evidence else []
            )
            self.edges[edge_id] = edge
            self.adjacency[source_id].add(target_id)
            self.adjacency[target_id].add(source_id)
        
        return edge_id
    
    def add_entities_from_page(self, entities: List[Dict], domain: str, url: str):
        """Ajoute toutes les entites d'une page et cree les liens de co-occurrence."""
        node_ids = []
        
        # Ajouter les entites
        for entity in entities:
            node_id = self.add_entity(
                entity_type=entity.get('type', 'unknown'),
                value=entity.get('value', ''),
                source_domain=domain,
                source_url=url,
                metadata=entity.get('metadata', {})
            )
            node_ids.append(node_id)
        
        # Creer les liens de co-occurrence
        for i, source_id in enumerate(node_ids):
            for target_id in node_ids[i+1:]:
                self.add_relationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship="co-occurrence",
                    evidence=f"Same page: {url}"
                )
    
    def get_node(self, entity_type: str, value: str) -> Optional[EntityNode]:
        """Recupere un noeud."""
        node_id = self._generate_node_id(entity_type, value)
        return self.nodes.get(node_id)
    
    def get_connected_entities(self, node_id: str, 
                               entity_type: str = None,
                               max_depth: int = 1) -> List[EntityNode]:
        """Recupere les entites connectees."""
        if node_id not in self.nodes:
            return []
        
        visited = {node_id}
        current_level = {node_id}
        results = []
        
        for _ in range(max_depth):
            next_level = set()
            for current_id in current_level:
                for neighbor_id in self.adjacency.get(current_id, set()):
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        next_level.add(neighbor_id)
                        
                        node = self.nodes.get(neighbor_id)
                        if node:
                            if entity_type is None or node.type == entity_type:
                                results.append(node)
            
            current_level = next_level
            if not current_level:
                break
        
        return results
    
    def get_entities_by_domain(self, domain: str) -> List[EntityNode]:
        """Recupere toutes les entites d'un domaine."""
        node_ids = self.domain_index.get(domain, set())
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]
    
    def get_entities_by_type(self, entity_type: str) -> List[EntityNode]:
        """Recupere toutes les entites d'un type."""
        node_ids = self.type_index.get(entity_type, set())
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]
    
    def get_cross_domain_entities(self, min_domains: int = 2) -> List[EntityNode]:
        """Recupere les entites presentes sur plusieurs domaines."""
        results = []
        for node in self.nodes.values():
            if len(node.source_domains) >= min_domains:
                results.append(node)
        
        return sorted(results, key=lambda n: len(n.source_domains), reverse=True)
    
    def get_stats(self) -> Dict:
        """Stats du graphe."""
        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'nodes_by_type': {t: len(ids) for t, ids in self.type_index.items()},
            'domains_indexed': len(self.domain_index),
            'cross_domain_entities': len(self.get_cross_domain_entities(2)),
            'avg_connections': sum(len(adj) for adj in self.adjacency.values()) / max(len(self.nodes), 1)
        }
    
    def to_dict(self) -> Dict:
        """Exporte le graphe en dict."""
        return {
            'nodes': [
                {
                    'id': n.id,
                    'type': n.type,
                    'value': n.value,
                    'occurrence_count': n.occurrence_count,
                    'source_domains': list(n.source_domains),
                    'risk_score': n.risk_score
                }
                for n in self.nodes.values()
            ],
            'edges': [
                {
                    'source': e.source_id,
                    'target': e.target_id,
                    'relationship': e.relationship,
                    'weight': e.weight
                }
                for e in self.edges.values()
            ],
            'stats': self.get_stats()
        }


class CorrelationEngine:
    """Moteur de correlation d'entites."""
    
    # Seuils de correlation
    THRESHOLDS = {
        'same_wallet_multiple_domains': 0.99,  # CRITICAL
        'same_email_5plus_domains': 0.95,
        'same_username_marketplace_forum': 0.75,
        'same_ip_domain_cluster': 0.80,
        'co_occurrence_same_page': 0.60,
    }
    
    def __init__(self, graph: EntityGraph):
        self.graph = graph
    
    def correlate_entities(self, entity1_id: str, entity2_id: str) -> CorrelationResult:
        """Calcule la correlation entre deux entites."""
        node1 = self.graph.nodes.get(entity1_id)
        node2 = self.graph.nodes.get(entity2_id)
        
        if not node1 or not node2:
            return CorrelationResult(
                entity1_id=entity1_id,
                entity2_id=entity2_id,
                correlation_score=0.0,
                confidence=0.0,
                relationship_type="unknown"
            )
        
        # Calculer les scores
        score = 0.0
        evidence = []
        relationship_type = "none"
        
        # 1. Domaines communs
        common_domains = node1.source_domains.intersection(node2.source_domains)
        if common_domains:
            domain_score = min(len(common_domains) * 0.2, 0.6)
            score += domain_score
            evidence.append(f"{len(common_domains)} common domains")
            relationship_type = "same_domain"
        
        # 2. Pages communes (URLs)
        common_urls = node1.source_urls.intersection(node2.source_urls)
        if common_urls:
            url_score = min(len(common_urls) * 0.3, 0.9)
            score += url_score
            evidence.append(f"{len(common_urls)} common pages")
            relationship_type = "same_page"
        
        # 3. Lien direct dans le graphe
        edge_id = self.graph._generate_edge_id(entity1_id, entity2_id)
        if edge_id in self.graph.edges:
            edge = self.graph.edges[edge_id]
            score += edge.weight * 0.2
            evidence.extend(edge.evidence[:3])
            relationship_type = edge.relationship
        
        # 4. Connexions indirectes (amis communs)
        neighbors1 = self.graph.adjacency.get(entity1_id, set())
        neighbors2 = self.graph.adjacency.get(entity2_id, set())
        common_neighbors = neighbors1.intersection(neighbors2)
        if common_neighbors:
            neighbor_score = min(len(common_neighbors) * 0.1, 0.3)
            score += neighbor_score
            evidence.append(f"{len(common_neighbors)} common connections")
        
        # Normaliser
        score = min(score, 1.0)
        
        # Confidence basee sur le volume de donnees
        data_volume = (node1.occurrence_count + node2.occurrence_count) / 2
        confidence = min(0.5 + (data_volume * 0.1), 0.95)
        
        # Interpretation
        interpretation = self._interpret_correlation(node1, node2, score)
        
        return CorrelationResult(
            entity1_id=entity1_id,
            entity2_id=entity2_id,
            correlation_score=round(score, 2),
            confidence=round(confidence, 2),
            relationship_type=relationship_type,
            evidence=evidence,
            interpretation=interpretation
        )
    
    def _interpret_correlation(self, node1: EntityNode, node2: EntityNode, score: float) -> str:
        """Interprete humainement la correlation."""
        if score >= 0.9:
            return f"CRITICAL: {node1.type} '{node1.value}' and {node2.type} '{node2.value}' are highly correlated"
        elif score >= 0.7:
            return f"HIGH: Strong correlation between {node1.type} and {node2.type}"
        elif score >= 0.4:
            return f"MEDIUM: Moderate correlation detected"
        elif score >= 0.2:
            return f"LOW: Weak correlation"
        else:
            return "No significant correlation"
    
    def find_clusters(self, entity_type: str = None, min_size: int = 3) -> List[List[str]]:
        """Trouve des clusters d'entites correlees."""
        visited = set()
        clusters = []
        
        nodes_to_check = list(self.graph.nodes.keys())
        if entity_type:
            nodes_to_check = list(self.graph.type_index.get(entity_type, set()))
        
        for node_id in nodes_to_check:
            if node_id in visited:
                continue
            
            cluster = self._bfs_cluster(node_id, visited)
            if len(cluster) >= min_size:
                clusters.append(cluster)
        
        return sorted(clusters, key=len, reverse=True)
    
    def _bfs_cluster(self, start_id: str, visited: Set[str]) -> List[str]:
        """BFS pour trouver un cluster."""
        cluster = []
        queue = [start_id]
        
        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            
            visited.add(node_id)
            cluster.append(node_id)
            
            for neighbor_id in self.graph.adjacency.get(node_id, set()):
                if neighbor_id not in visited:
                    queue.append(neighbor_id)
        
        return cluster
    
    def find_high_risk_correlations(self, min_score: float = 0.7) -> List[CorrelationResult]:
        """Trouve les correlations a haut risque."""
        results = []
        
        # Wallets sur plusieurs domaines
        for node in self.graph.get_cross_domain_entities(3):
            if node.type in ('bitcoin', 'monero', 'ethereum'):
                for other_id in self.graph.adjacency.get(node.id, set()):
                    corr = self.correlate_entities(node.id, other_id)
                    if corr.correlation_score >= min_score:
                        results.append(corr)
        
        # Emails sur 5+ domaines
        for node in self.graph.get_cross_domain_entities(5):
            if node.type == 'email':
                results.append(CorrelationResult(
                    entity1_id=node.id,
                    entity2_id="",
                    correlation_score=0.95,
                    confidence=0.9,
                    relationship_type="cross_domain_presence",
                    evidence=[f"Found on {len(node.source_domains)} domains"],
                    interpretation=f"CRITICAL: Email '{node.value}' found on {len(node.source_domains)} different domains"
                ))
        
        return sorted(results, key=lambda r: r.correlation_score, reverse=True)
    
    def get_entity_profile(self, node_id: str) -> Dict:
        """Profil complet d'une entite avec correlations."""
        node = self.graph.nodes.get(node_id)
        if not node:
            return {}
        
        connected = self.graph.get_connected_entities(node_id, max_depth=2)
        
        correlations = []
        for connected_node in connected[:10]:
            corr = self.correlate_entities(node_id, connected_node.id)
            if corr.correlation_score > 0.2:
                correlations.append({
                    'entity': connected_node.value,
                    'type': connected_node.type,
                    'score': corr.correlation_score,
                    'relationship': corr.relationship_type
                })
        
        return {
            'entity': {
                'id': node.id,
                'type': node.type,
                'value': node.value,
                'occurrence_count': node.occurrence_count,
                'source_domains': list(node.source_domains),
                'first_seen': node.first_seen,
                'last_seen': node.last_seen,
                'risk_score': node.risk_score
            },
            'correlations': sorted(correlations, key=lambda c: c['score'], reverse=True),
            'connected_count': len(connected),
            'cross_domain': len(node.source_domains) >= 2
        }


# Instances globales
entity_graph = EntityGraph()
correlation_engine = CorrelationEngine(entity_graph)

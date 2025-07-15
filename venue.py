import re
from typing import Dict, List, Optional
from rapidfuzz import fuzz, process
import spacy
from collections import defaultdict

class VenueNormalizer:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.venue_db = self.venue_database()

    def venue_database(self):
        return {
            'NUS Sports Centre': ['sports centre', 'nus sports', 'nus gym'],
            'USC Sports Hall': ['usc hall', 'univeristy sports centre'],
            'UTown Sports Hall': ['utown hall', 'univerity town'],
            'ActiveSG Yishun' : ["yishun sports hall", 'yishun gym'],
            'ActiveSG Clementi' : ['clementi sports hall']
        }
    
    def normalize_venue(self, raw_input: str) -> str:
        if not raw_input or not isinstance(raw_input,str):
            return ""
        
        cleaned = re.sub(r'\s+', ' ', raw_input.lower().strip())

        for propoer_name, aliases in self.venue_db.items():
            if cleaned in [a.lower() for a in aliases + [propoer_name]]:
                return propoer_name
        
        best_match, score = process.extractOne(
            cleaned,
            list(self.venue_db.keys()),
            scorer=fuzz.token_set_ratio
        )

        return best_match if score > 70 else cleaned.title()
    
    def suggest_venues(self, query: str) -> List[str]:
        matches = []
        for venue, aliases in self.venue_db.items():
            if query.lower() in venue.lower():
                matches.append(venue)
            for alias in aliases:
                if query.lower() in alias.lower():
                    matches.append(f"{alias} ({venue})")
        return sorted(list(set(matches)))[:5] #Return max 5 suggestions

class VenueAutocomplete:
    def __init__(self, normalizer: VenueNormalizer):
        self.nomralizer = normalizer
        self.venue_index = self._buld_venue_index()
    
    def _build_venue_index(self) -> List[str]:
        venues = set()

        for category, venue_list in self.nomralizer.venue_hierarchy.items():
            venues.add(category)
            venues.update(venue_list)
        
        variations = [
            "NUS", "National Univesity of Singapore",
            "ActiveSG", "SportsSG", "Community Club"
        ]
        venues.update(variations)
        return sorted(venues)
    
    def suggest_venues(self, query: str, limit: int = 5) -> List[str]:
        if not query:
            return []
        
        normalized_query = self.nomralizer.normalize_venue(query)

        results = process.extract(
            normalized_query,
            self.venue_index,
            scorer = fuzz.token_sort_ratio,
            limit=limit
        )

        return [venue for venue, score in results if score > 60]

class VenueSearchEngine:
    def __init__(self, normalizer: VenueNormalizer):
        self.normalizer = normalizer
        self.nlp = spacy.load("en_core_web_sm")
    
    def search_venues(self, query: str, venues: List[str], limit: int = 5) -> List[str]:
        if not query or not venues:
            return []
           
        normalized_venues = [(v, self.normalizer.normalize_venue(v)) for v in venues]
        query_doc = self.nlp(query.lower())
        query_tokens = {token.lemma_ for token in query.doc
                        if not token.is_stop and not token.is_punct}
        
        scored_venues = []
        for original, normalized in normalized_venues:
            norm_doc = self.nlp(normalized.lower())
            norm_tokens = {token.lemma_ for token in norm_doc
                           if not token.is_stop and not token.is_punct}
            
            #Exact match score
            exact_score = fuzz.ratio(query.lower(), normalized.lower()) / 100
            #Token overlap score
            overlap = len(query_tokens & norm_tokens) / len(query_tokens) if query_tokens else 0
            #Fuzzy match score
            fuzzy_score = fuzz.token_set_ratio(query, normalized) / 100
            #Combined score
            combined_score = 0.4 * exact_score +0.3 * overlap +0.3*fuzzy_score
            scored_venues.append((original, combined_score))

        scored_venues.sort(key=lambda x: x[1], reverse=True)
        return [v[0] for v in scored_venues[:limit] if v[1] > 0.3]



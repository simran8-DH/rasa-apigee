
"""
Insurance Quotation Bot - Custom Actions
This file contains all the custom actions that the bot performs when collecting quotation details.

EXECUTION FLOW:
1. User requests quotation -> ActionActivateQuotationForm runs
2. Form starts collecting data -> ValidateQuotationForm.validate_* methods run
3. When form is complete -> ActionSubmitQuotationForm runs
4. User confirms -> ActionCallPremiumApi runs to get premium
"""

import re
import json
from datetime import datetime
from rasa_sdk.events import SlotSet, ActiveLoop
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Action, Tracker, FormValidationAction
from typing import Any, Dict, List
from actions.api_utils_noED import get_cached_token, call_main_api
from rasa_sdk.types import DomainDict
from actions.properties import API_URL


class ActionActivateQuotationForm(Action):
    """
    FIRST ACTION: Called when user asks for a quotation.
    - If all slots are filled: Shows summary directly
    - Otherwise: Shows instructions to collect details
    """
    
    def name(self) -> str:
        return "action_activate_quotation_form"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[str, Any]]:
        
        required_slots = ["first_name", "last_name", "dob_quotation", "gender", 
                         "marital_status", "tobacco", "sum_assured", "term", "ppt"]
        
        all_filled = all(tracker.get_slot(slot) is not None and tracker.get_slot(slot) != "" 
                        for slot in required_slots)
        
        if all_filled:
            product = "ICICI PRU IPROTECT SMART PLUS"
            mode = "Annually"
            dispatcher.utter_message(
                text=(
                    "*Quotation Summary*\n"
                    f"*Product:* {product}\n"
                    f"*Sum Assured:* {tracker.get_slot('sum_assured')}\n"
                    f"*Term:* {tracker.get_slot('term')} years\n"
                    f"*Tobacco:* {tracker.get_slot('tobacco')}\n"
                    f"*Mode:* {mode}\n"
                    "*Should I proceed to get your premium?* (proceed/stop)"
                )
            )
            return [
                ActiveLoop(None),
                SlotSet("awaiting_premium_confirmation", True)
            ]
        
        message = (
            "Great! I'll help you get a quotation. Please provide me with the following details:\n"
            "• Name (First and Last name)\n"
            "• Date of Birth (e.g., 1987/04/06 or 12 june 1992)\n"
            "• Gender (Male/Female)\n"
            "• Marital Status (Married/Single)\n"
            "• Tobacco consumption (Yes/No)\n"
            "• Policy Term (e.g., 20 years)\n"
            "• Premium Payment Term (PPT) (e.g., 10 years)\n"
            "• Sum Assured (e.g., 5000000)\n"
            "You can provide all these details in a single comma-separated message or can chat.\n"
        )
        dispatcher.utter_message(text=message)
        return []


class ValidateQuotationForm(FormValidationAction):
    """
    MAIN VALIDATION CLASS: Called by Rasa for each slot validation.
    
    EXECUTION ORDER:
    1. User sends message (single value OR comma-separated)
    2. Rasa calls validate_* method for requested slot
    3. validate_* method calls _normalize_comma_input() to clean input
    4. validate_* method calls _extract_entities() to find all entities
    5. If comma-separated input detected, _extract_all_slots() extracts everything at once
    6. Returns validated slot value(s)
    """

    def name(self):
        return "validate_quotation_form"

    def _normalize_comma_input(self, text: str) -> List[str]:
        """
        STEP 1: Normalize comma-separated input.
        - Splits by commas
        - Removes extra spaces (handles both "value, value" and "value,value")
        - Returns list of cleaned parts
        """
        if not text:
            return []
        
        # Split by comma and strip each part
        parts = [part.strip() for part in text.split(',')]
        # Remove empty parts
        parts = [p for p in parts if p]
        return parts

    def _parse_date_to_iso(self, date_str: str) -> str:
        """
        STEP 2: Parse any date format and convert to YYYY-MM-DD (ISO format for API).
        Handles formats like:
        - 12 june 1992 (DD Month YYYY)
        - june 12 2002 (Month DD YYYY)
        - 2000 june 10 (YYYY Month DD)
        - 2002 12 june (YYYY DD Month)
        - 1992-06-12 (YYYY-MM-DD)
        - 1992/06/12 (YYYY/MM/DD)
        - 12-06-1992 (DD-MM-YYYY)
        """
        if not date_str:
            return None
        
        # Clean the date string
        date_clean = re.sub(r'\s+', ' ', date_str.strip())
        
        # Try multiple date formats
        date_formats = [
            "%d %B %Y",      # 12 june 1992
            "%d %b %Y",      # 12 Jun 1992
            "%B %d %Y",      # june 12 2002
            "%b %d %Y",      # Jun 12 2002
            "%Y %B %d",      # 2000 june 10
            "%Y %b %d",      # 2000 Jun 10
            "%Y %d %B",      # 2002 12 june
            "%Y %d %b",      # 2002 12 Jun
            "%Y-%m-%d",      # 1992-06-12
            "%Y/%m/%d",      # 1992/06/12
            "%d-%m-%Y",      # 12-06-1992
            "%d/%m/%Y",      # 12/06/1992
            "%Y %m %d",      # 1992 06 12
            "%d %m %Y",      # 12 06 1992
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_clean, fmt).date()
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # Fallback: Try regex patterns for natural language dates
        # Pattern: YYYY DD Month (e.g., 1992 12 june)
        match = re.search(
            r'\b(\d{4})\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
            date_clean,
            re.IGNORECASE
        )
        if match:
            year, day, month_name = match.group(1), match.group(2), match.group(3)
            month_num = self._month_to_num(month_name)
            return f"{year}-{month_num:02d}-{int(day):02d}"
        
        # Pattern: DD Month YYYY (e.g., 12 june 1992)
        match = re.search(
            r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b',
            date_clean,
            re.IGNORECASE
        )
        if match:
            day, month_name, year = match.group(1), match.group(2), match.group(3)
            month_num = self._month_to_num(month_name)
            return f"{year}-{month_num:02d}-{int(day):02d}"
        
        # Pattern: YYYY-MM-DD or YYYY/MM/DD
        match = re.search(r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b', date_clean)
        if match:
            year, month, day = match.group(1), match.group(2), match.group(3)
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        return None

    def _month_to_num(self, month_str: str) -> int:
        """Helper: Convert month name to number (1-12)."""
        months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        return months.get(month_str.lower(), 1)

    def _extract_entities(self, tracker: Tracker) -> Dict[str, Any]:
        """
        STEP 3: Extract all entities from user message.
        - First gets entities from Rasa NLU
        - Then uses regex to find missing entities
        - Returns dictionary of extracted entities
        """
        latest_message = tracker.latest_message
        full_text = latest_message.get("text", "") or ""
        text_lower = full_text.lower()
        
        extracted = {}
        
        # Get entities from Rasa NLU first
        entities = latest_message.get("entities", [])
        for entity in entities:
            entity_name = entity.get("entity")
            entity_value = entity.get("value")
            if entity_name and entity_value:
                extracted[entity_name] = entity_value
        
        # Extract names (first two words at start, before first comma)
        # For comma-separated input, always extract from first part (ignore NLU if wrong)
        if ',' in full_text:
            name_text = full_text.split(',')[0].strip()
            # Extract only first two words (names should be just two words)
            name_match = re.search(r'^([a-zA-Z]+)\s+([a-zA-Z]+)\b', name_text)
            if name_match:
                extracted["first_name"] = name_match.group(1).capitalize()
                extracted["last_name"] = name_match.group(2).capitalize()
        elif "first_name" not in extracted or "last_name" not in extracted:
            # No comma - extract from full text
            name_text = full_text.strip()
            name_match = re.search(r'^([a-zA-Z]+)\s+([a-zA-Z]+)\b', name_text)
            if name_match:
                if "first_name" not in extracted:
                    extracted["first_name"] = name_match.group(1).capitalize()
                if "last_name" not in extracted:
                    extracted["last_name"] = name_match.group(2).capitalize()
        
        # Extract DOB - try parsing each comma-separated part first, then full text
        if "dob_quotation" not in extracted:
            # If comma-separated, check each part individually
            if ',' in full_text:
                parts = self._normalize_comma_input(full_text)
                for part in parts:
                    dob_iso = self._parse_date_to_iso(part)
                    if dob_iso:
                        extracted["dob_quotation"] = dob_iso
                        break
            else:
                # No commas, parse full text
                dob_iso = self._parse_date_to_iso(full_text)
                if dob_iso:
                    extracted["dob_quotation"] = dob_iso
        
        # Extract gender
        if "gender" not in extracted:
            if re.search(r'\b(male|m)\b', text_lower):
                extracted["gender"] = "Male"
            elif re.search(r'\b(female|f)\b', text_lower):
                extracted["gender"] = "Female"
        
        # Extract marital status
        if "marital_status" not in extracted:
            if re.search(r'\b(married|m)\b', text_lower):
                extracted["marital_status"] = "Married"
            elif re.search(r'\b(single|s)\b', text_lower):
                extracted["marital_status"] = "Single"
        
        # Extract tobacco
        if "tobacco" not in extracted:
            if re.search(r'\b(yes|y|do|does)\s+tobacco\b', text_lower) or re.search(r',\s*(yes|y)\s*,', text_lower):
                extracted["tobacco"] = "Yes"
            elif re.search(r'\b(no|n|don\'t|dont|doesn\'t|does not|do not)\s+tobacco\b', text_lower) or re.search(r',\s*(no|n)\s*,', text_lower):
                extracted["tobacco"] = "No"
        
        # Extract sum assured (large numbers: 6-12 digits, minimum 500000)
        if "sum_assured" not in extracted:
            sa_matches = re.findall(r'\b(\d{6,12})\b', full_text)
            for match in reversed(sa_matches):
                num = int(match)
                if 500000 <= num <= 999999999999:
                    extracted["sum_assured"] = match
                    break
        
        # Extract term and PPT - CRITICAL: Compare numbers, bigger = term, smaller = PPT
        # First, try keyword-based extraction (most reliable) - only if not comma-separated
        has_commas = ',' in full_text
        if not has_commas:
            if "term" not in extracted:
                term_match = re.search(r'\b(\d{1,2})\s*(?:years?)?\s*term\b', full_text, re.IGNORECASE)
                if term_match:
                    num = int(term_match.group(1))
                    if 5 <= num <= 40:
                        extracted["term"] = num
            
            if "ppt" not in extracted:
                ppt_match = re.search(r'\b(\d{1,2})\s*ppt\b', full_text, re.IGNORECASE)
                if ppt_match:
                    num = int(ppt_match.group(1))
                    if 1 <= num <= 40:
                        extracted["ppt"] = num
        
        # For comma-separated input OR if keywords didn't work, find all small numbers (1-40)
        # Exclude dates and sum assured
        if has_commas or "term" not in extracted or "ppt" not in extracted:
            small_numbers = []
            parts = self._normalize_comma_input(full_text)
            
            for part in parts:
                part_clean = part.strip()
                # Skip if it's a date (check if parsing succeeds)
                if self._parse_date_to_iso(part_clean):
                    continue
                # Skip if it's sum assured (large number - 6+ digits)
                if re.search(r'\d{6,}', part_clean):
                    continue
                # Skip if it contains text that's clearly not a number (like "female", "male", "yes", "no", etc.)
                if re.search(r'\b(female|male|yes|no|married|single|m|f|y|n)\b', part_clean, re.IGNORECASE):
                    continue
                # Check if the part is ONLY a number (or number with whitespace)
                # This ensures we only extract standalone numbers, not numbers embedded in text
                part_numbers_only = re.sub(r'[^\d]', '', part_clean)
                if part_numbers_only and len(part_numbers_only) <= 2:
                    num = int(part_numbers_only)
                    if 1 <= num <= 40:
                        small_numbers.append(num)
            
            # Remove duplicates and sort descending
            small_numbers = sorted(set(small_numbers), reverse=True)
            
            # Debug output
            if small_numbers:
                print(f"[DEBUG] Found small numbers for term/PPT: {small_numbers}")
            
            # CRITICAL: If we found 2+ numbers in comma-separated input, ALWAYS override both
            # Bigger = term, smaller = PPT (regardless of what was extracted before)
            if len(small_numbers) >= 2:
                if has_commas:
                    # Comma-separated input: ALWAYS set both based on comparison
                    extracted["term"] = small_numbers[0]  # Biggest = term (int)
                    extracted["ppt"] = small_numbers[1]  # Second biggest = PPT (int)
                    print(f"[DEBUG] Comma-separated input: Setting term = {small_numbers[0]} (biggest), ppt = {small_numbers[1]} (second biggest)")
                else:
                    # Not comma-separated: only set if not already extracted
                    if "term" not in extracted:
                        extracted["term"] = small_numbers[0]
                        print(f"[DEBUG] Setting term = {small_numbers[0]} (biggest)")
                    if "ppt" not in extracted:
                        extracted["ppt"] = small_numbers[1]
                        print(f"[DEBUG] Setting ppt = {small_numbers[1]} (second biggest)")
            elif len(small_numbers) == 1:
                # Only one number found - assign to term if in range (5-40), leave PPT empty so form asks for it
                num = small_numbers[0]
                if 5 <= num <= 40 and "term" not in extracted:
                    extracted["term"] = num
                    # Explicitly don't set PPT - form will ask for it
                    print(f"[DEBUG] Setting term = {num} (only number found, in term range). PPT will be asked by form.")
                elif 1 <= num < 5 and "ppt" not in extracted:
                    # If number is 1-4, it can only be PPT (term minimum is 5)
                    extracted["ppt"] = num
                    print(f"[DEBUG] Setting ppt = {num} (only number found, too small for term)")
                # If number is 1-4 and term not set, we still don't set PPT automatically
                # Let the form ask for term first
        
        return extracted

    def _extract_all_slots(self, tracker: Tracker) -> Dict[str, Any]:
        """
        STEP 4: Extract all slots from comma-separated input.
        Called when user provides multiple values at once.
        Never overwrites existing slot values (user might be answering one by one).
        """
        latest_message = tracker.latest_message
        full_text = latest_message.get("text", "") or ""
        
        # Only process if comma-separated input detected
        if ',' not in full_text:
            return {}
        
        # Normalize comma input
        parts = self._normalize_comma_input(full_text)
        if len(parts) < 2:
            return {}
        
        # Extract all entities
        entities = self._extract_entities(tracker)
        slot_values = {}
        
        # Set slots only if they're currently empty (don't overwrite)
        if "first_name" in entities and not tracker.get_slot("first_name"):
            first_name_clean = re.sub(r'[^a-zA-Z\s-]', '', str(entities["first_name"])).strip()
            # Extract first word only (names should be single words)
            first_name_parts = first_name_clean.split()
            if first_name_parts:
                slot_values["first_name"] = first_name_parts[0].capitalize()
        
        if "last_name" in entities and not tracker.get_slot("last_name"):
            last_name_clean = re.sub(r'[^a-zA-Z\s-]', '', str(entities["last_name"])).strip()
            # Extract first word only (names should be single words)
            last_name_parts = last_name_clean.split()
            if last_name_parts:
                slot_values["last_name"] = last_name_parts[0].capitalize()
        
        if "dob_quotation" in entities and not tracker.get_slot("dob_quotation"):
            dob_value = str(entities["dob_quotation"])
            # Only parse if it looks like a date (contains month name, slashes, dashes, or is YYYY-MM-DD format)
            if any(char in dob_value.lower() for char in ['/', '-']) or \
               any(month in dob_value.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']) or \
               re.match(r'^\d{4}-\d{2}-\d{2}$', dob_value):
                dob_iso = self._parse_date_to_iso(dob_value)
                if dob_iso:
                    slot_values["dob_quotation"] = dob_iso
        
        if "gender" in entities and not tracker.get_slot("gender"):
            gender = str(entities["gender"]).lower()
            slot_values["gender"] = "Male" if gender in ["male", "m"] else "Female" if gender in ["female", "f"] else gender.capitalize()
        
        if "marital_status" in entities and not tracker.get_slot("marital_status"):
            status = str(entities["marital_status"]).lower()
            if not re.fullmatch(r"\d{2,4}", status):  # Ignore numeric values (years)
                slot_values["marital_status"] = "Married" if status in ["married", "m"] else "Single" if status in ["single", "s"] else status.capitalize()
        
        if "tobacco" in entities and not tracker.get_slot("tobacco"):
            tobacco_val = str(entities["tobacco"]).lower()
            slot_values["tobacco"] = "Yes" if tobacco_val in ["yes", "y", "do", "does"] else "No"
        
        if "sum_assured" in entities and not tracker.get_slot("sum_assured"):
            sa_str = str(entities["sum_assured"])
            numbers = re.findall(r'\d+', sa_str)
            if numbers:
                sa_value = float(''.join(numbers))
                if sa_value >= 500000:
                    slot_values["sum_assured"] = sa_value
        
        if "term" in entities and not tracker.get_slot("term"):
            term_value = int(entities["term"]) if isinstance(entities["term"], str) else entities["term"]
            if 5 <= term_value <= 40:
                slot_values["term"] = term_value
        
        if "ppt" in entities and not tracker.get_slot("ppt"):
            ppt_num = int(entities["ppt"]) if isinstance(entities["ppt"], str) else entities["ppt"]
            if 1 <= ppt_num <= 40:
                slot_values["ppt"] = str(ppt_num)
        
        return slot_values

    # ========== VALIDATION METHODS (called by Rasa for each slot) ==========

    def validate_first_name(self, value, dispatcher, tracker, domain):
        """Validates first name. If comma-separated input, extracts all slots at once."""
        # Check for comma-separated input first
        if ',' in (tracker.latest_message.get("text", "") or ""):
            all_slots = self._extract_all_slots(tracker)
            if all_slots:
                return all_slots
        
        entities = self._extract_entities(tracker)
        
        # If both names found, return both (but only take first word of each)
        if "first_name" in entities and "last_name" in entities:
            first_name_clean = re.sub(r'[^a-zA-Z\s-]', '', str(entities["first_name"])).strip()
            last_name_clean = re.sub(r'[^a-zA-Z\s-]', '', str(entities["last_name"])).strip()
            # Only take first word of each
            first_name_parts = first_name_clean.split()
            last_name_parts = last_name_clean.split()
            if first_name_parts and last_name_parts:
                return {"first_name": first_name_parts[0].capitalize(), "last_name": last_name_parts[0].capitalize()}
        
        # If only first name found (only take first word)
        if "first_name" in entities:
            first_name_clean = re.sub(r'[^a-zA-Z\s-]', '', str(entities["first_name"])).strip()
            first_name_parts = first_name_clean.split()
            if first_name_parts:
                return {"first_name": first_name_parts[0].capitalize()}
        
        # If value has space, might be full name - split it
        if value and isinstance(value, str) and ' ' in value.strip():
            name_parts = value.split()
            if len(name_parts) >= 2:
                first_name = re.sub(r'[^a-zA-Z\s-]', '', name_parts[0]).strip()
                last_name = re.sub(r'[^a-zA-Z\s-]', '', name_parts[1]).strip()
                if first_name and last_name:
                    return {"first_name": first_name, "last_name": last_name}
        
        # Clean and return as first name
        if value:
            cleaned = re.sub(r'[^a-zA-Z\s-]', '', str(value)).strip()
            if cleaned:
                return {"first_name": cleaned}
        
        return {"first_name": value}

    def validate_last_name(self, value, dispatcher, tracker, domain):
        """Validates last name."""
        entities = self._extract_entities(tracker)
        
        if "last_name" in entities:
            last_name = re.sub(r'[^a-zA-Z\s-]', '', str(entities["last_name"])).strip()
            if last_name:
                return {"last_name": last_name}
        
        # Keep existing last name if already set
        existing = tracker.get_slot("last_name")
        if existing:
            cleaned = re.sub(r'[^a-zA-Z\s-]', '', str(existing)).strip()
            if cleaned:
                return {"last_name": cleaned}
        
        if value:
            cleaned = re.sub(r'[^a-zA-Z\s-]', '', str(value)).strip()
            if cleaned:
                return {"last_name": cleaned}
        
        return {"last_name": value}

    def validate_dob_quotation(self, value, dispatcher, tracker, domain):
        """Validates DOB. Converts any format to YYYY-MM-DD."""
        # Check for comma-separated input first - extract all slots at once
        full_text = tracker.latest_message.get("text", "") or ""
        if ',' in full_text:
            all_slots = self._extract_all_slots(tracker)
            if "dob_quotation" in all_slots:
                return {"dob_quotation": all_slots["dob_quotation"]}
        
        entities = self._extract_entities(tracker)
        
        # Try to parse DOB - but validate it looks like a date first
        dob_iso = None
        
        # Check entity value - only parse if it looks like a date
        if "dob_quotation" in entities:
            dob_value = str(entities["dob_quotation"])
            # Only parse if it looks like a date (not just a number like "24")
            if any(char in dob_value.lower() for char in ['/', '-']) or \
               any(month in dob_value.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']) or \
               re.match(r'^\d{4}-\d{2}-\d{2}$', dob_value):
                dob_iso = self._parse_date_to_iso(dob_value)
        
        # If not found in entities, try parsing each comma-separated part
        if not dob_iso and ',' in full_text:
            parts = self._normalize_comma_input(full_text)
            for part in parts:
                dob_iso = self._parse_date_to_iso(part)
                if dob_iso:
                    break
        
        # If still not found, try full text
        if not dob_iso:
            dob_iso = self._parse_date_to_iso(full_text)
        
        # Last resort: try value parameter (but validate it looks like a date)
        if not dob_iso and value:
            value_str = str(value)
            # Only parse if it looks like a date
            if any(char in value_str.lower() for char in ['/', '-']) or \
               any(month in value_str.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']) or \
               re.match(r'^\d{4}-\d{2}-\d{2}$', value_str):
                dob_iso = self._parse_date_to_iso(value_str)
        
        if dob_iso and re.match(r'\d{4}-\d{2}-\d{2}', dob_iso):
            return {"dob_quotation": dob_iso}
        
        # If we have an existing valid DOB, keep it
        existing_dob = tracker.get_slot("dob_quotation")
        if existing_dob and re.match(r'\d{4}-\d{2}-\d{2}', str(existing_dob)):
            return {"dob_quotation": existing_dob}
        
        return {"dob_quotation": value}

    def validate_gender(self, value, dispatcher, tracker, domain):
        """Validates gender."""
        entities = self._extract_entities(tracker)
        
        if "gender" in entities:
            gender = str(entities["gender"]).lower()
            if gender in ["male", "m"]:
                return {"gender": "Male"}
            elif gender in ["female", "f"]:
                return {"gender": "Female"}
        
        if value:
            gender = str(value).lower()
            if gender in ["male", "m"]:
                return {"gender": "Male"}
            elif gender in ["female", "f"]:
                return {"gender": "Female"}
        
        return {"gender": value}

    def validate_marital_status(self, value, dispatcher, tracker, domain):
        """Validates marital status."""
        entities = self._extract_entities(tracker)
        
        if "marital_status" in entities:
            status = str(entities["marital_status"]).lower()
            if not re.fullmatch(r"\d{2,4}", status):  # Ignore numeric values
                if status in ["married", "m"]:
                    return {"marital_status": "Married"}
                elif status in ["single", "s"]:
                    return {"marital_status": "Single"}
        
        if value:
            status = str(value).lower()
            if not re.fullmatch(r"\d{2,4}", status):
                if status in ["married", "m"]:
                    return {"marital_status": "Married"}
                elif status in ["single", "s"]:
                    return {"marital_status": "Single"}
        
        return {"marital_status": value}

    def validate_tobacco(self, value, dispatcher, tracker, domain):
        """Validates tobacco consumption."""
        entities = self._extract_entities(tracker)
        
        if "tobacco" in entities:
            tobacco = str(entities["tobacco"]).lower()
            if tobacco in ["yes", "y", "do", "does"]:
                return {"tobacco": "Yes"}
            elif tobacco in ["no", "n", "don't", "dont"]:
                return {"tobacco": "No"}
        
        if value:
            tobacco = str(value).lower()
            if tobacco in ["yes", "y", "do", "does"]:
                return {"tobacco": "Yes"}
            elif tobacco in ["no", "n", "don't", "dont"]:
                return {"tobacco": "No"}
        
        return {"tobacco": value}

    def validate_sum_assured(self, value, dispatcher, tracker, domain):
        """Validates sum assured (minimum 500000)."""
        entities = self._extract_entities(tracker)
        
        if "sum_assured" in entities:
            sa_str = str(entities["sum_assured"])
            numbers = re.findall(r'\d+', sa_str)
            if numbers:
                sa_value = float(''.join(numbers))
                if sa_value >= 500000:
                    return {"sum_assured": sa_value}
                else:
                    dispatcher.utter_message("Minimum sum assured is 5 lakhs.")
        
        if value:
            numbers = re.findall(r'\d+', str(value))
            if numbers:
                sa_value = float(''.join(numbers))
                if sa_value >= 500000:
                    return {"sum_assured": sa_value}
                else:
                    dispatcher.utter_message("Minimum sum assured is 5 lakhs.")
        
        return {"sum_assured": value}

    def validate_term(self, value, dispatcher, tracker, domain):
        """Validates policy term (5-40 years)."""
        # Don't process if form is asking for PPT
        if tracker.get_slot("requested_slot") == "ppt":
            existing = tracker.get_slot("term")
            return {"term": existing} if existing is not None else {}
        
        # Check for comma-separated input first - extract all slots at once
        full_text = tracker.latest_message.get("text", "") or ""
        if ',' in full_text:
            all_slots = self._extract_all_slots(tracker)
            if "term" in all_slots:
                return {"term": all_slots["term"]}
        
        entities = self._extract_entities(tracker)
        
        # Prioritize extracted entities over value parameter
        if "term" in entities:
            term_value = int(entities["term"]) if isinstance(entities["term"], str) else entities["term"]
            if 5 <= term_value <= 40:
                return {"term": term_value}
            else:
                dispatcher.utter_message("Term must be between 5 and 40 years.")
        
        # Only use value parameter if no entity found
        if value and "term" not in entities:
            term_value = int(value) if isinstance(value, str) else value
            if 5 <= term_value <= 40:
                return {"term": term_value}
            else:
                dispatcher.utter_message("Term must be between 5 and 40 years.")
        
        existing = tracker.get_slot("term")
        if existing is not None:
            return {"term": existing}
        
        return {"term": value}

    def validate_ppt(self, value, dispatcher, tracker, domain):
        """Validates Premium Payment Term (PPT) (1-40 years)."""
        # Don't process if form is asking for term
        if tracker.get_slot("requested_slot") == "term":
            existing = tracker.get_slot("ppt")
            return {"ppt": existing} if existing is not None else {}
        
        # Check for comma-separated input first - extract all slots at once
        full_text = tracker.latest_message.get("text", "") or ""
        if ',' in full_text:
            all_slots = self._extract_all_slots(tracker)
            if "ppt" in all_slots:
                return {"ppt": all_slots["ppt"]}
        
        entities = self._extract_entities(tracker)
        
        # Prioritize extracted entities over value parameter
        if "ppt" in entities:
            ppt_num = int(entities["ppt"]) if isinstance(entities["ppt"], str) else entities["ppt"]
            if 1 <= ppt_num <= 40:
                return {"ppt": str(ppt_num)}
            else:
                dispatcher.utter_message("PPT must be between 1 and 40 years.")
        
        # Only use value parameter if no entity found
        if value and "ppt" not in entities:
            ppt_num = int(value) if isinstance(value, str) else value
            if 1 <= ppt_num <= 40:
                return {"ppt": str(ppt_num)}
            else:
                dispatcher.utter_message("PPT must be between 1 and 40 years.")
        
        existing = tracker.get_slot("ppt")
        if existing:
            return {"ppt": existing}
        
        # If no PPT found and no value provided, return empty dict so form asks for it
        if not value:
            return {}
        
        return {"ppt": value}


class ActionStopPremium(Action):
    """Called when user says 'stop' to premium calculation."""
    
    def name(self) -> str:
        return "action_stop_premium"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[str, Any]]:
        
        dispatcher.utter_message(text="Okay, I've stopped the premium calculation. If you need a quotation later, just let me know!")
        return [SlotSet("awaiting_premium_confirmation", False)]


class ActionSubmitQuotationForm(Action):
    """Called when form is complete. Shows summary and asks for confirmation."""
    
    def name(self) -> str:
        return "action_submit_quotation_form"
    
    def run(self, dispatcher, tracker, domain):
        product = "ICICI PRU IPROTECT SMART PLUS"
        mode = "Monthly"
        
        dispatcher.utter_message(
            text=(
                "*Quotation Summary*\n"
                f"*Product:* {product}\n"
                f"*Sum Assured:* {tracker.get_slot('sum_assured')}\n"
                f"*Term:* {tracker.get_slot('term')} years\n"
                f"*Tobacco:* {tracker.get_slot('tobacco')}\n"
                f"*Mode:* {mode}\n"
                "*Should I proceed to get your premium?* (proceed/stop)"
            )
        )
        return [SlotSet("awaiting_premium_confirmation", True)]


class ActionCallPremiumApi(Action):
    """
    FINAL ACTION: Called when user confirms premium calculation.
    Calls external API to get premium and displays result.
    """
    
    def name(self) -> str:
        return "action_call_premium_api"
    
    def _convert_to_int_string(self, value, default="0"):
        """Helper: Convert value to integer string (API requirement)."""
        if value is None:
            return default
        try:
            if isinstance(value, str):
                cleaned = re.sub(r'[^\d.]', '', value)
                if cleaned:
                    return str(int(float(cleaned)))
            else:
                return str(int(float(value)))
        except (ValueError, TypeError):
            return default
    
    def run(self, dispatcher, tracker, domain):
        # Collect and clean all inputs
        dob_raw = tracker.get_slot("dob_quotation") or ""
        # Validate DOB is in correct format (YYYY-MM-DD), not just a number
        dob = ""
        if dob_raw and re.match(r'^\d{4}-\d{2}-\d{2}$', str(dob_raw)):
            dob = str(dob_raw)
        else:
            dispatcher.utter_message("❌ Invalid date of birth. Please provide a valid date.")
            return [SlotSet("awaiting_premium_confirmation", False)]
        
        # Clean names - only take first word
        first_name_raw = str(tracker.get_slot("first_name") or "").strip()
        first_name_parts = re.sub(r'[^a-zA-Z\s-]', '', first_name_raw).strip().split()
        first_name = first_name_parts[0].capitalize() if first_name_parts else ""
        
        last_name_raw = str(tracker.get_slot("last_name") or "").strip()
        last_name_parts = re.sub(r'[^a-zA-Z\s-]', '', last_name_raw).strip().split()
        last_name = last_name_parts[0].capitalize() if last_name_parts else ""
        
        gender = str(tracker.get_slot("gender") or "")
        marital_status = str(tracker.get_slot("marital_status") or "")
        if re.fullmatch(r"\d{2,4}", marital_status):
            marital_status = ""
        else:
            marital_status_lower = marital_status.lower()
            if marital_status_lower in ["married", "m"]:
                marital_status = "Married"
            elif marital_status_lower in ["single", "s"]:
                marital_status = "Single"
            else:
                marital_status = marital_status.capitalize()
        
        # Build API payload
        data = {
            "Root": {
                "FirstName": first_name,
                "LastName": last_name,
                "DateOfBirth": dob,
                "Gender": gender,
                "MaritalStatus": marital_status,
                "PolicyholderFName": "",
                "PolicyholderLName": "",
                "PolicyholderDOB": "",
                "PolicyholderGender": "",
                "isNRI": "false",
                "isPolicyholder": "",
                "Staff": "0",
                "ProductDetails": {
                    "Product": {
                        "ProductType": "TRADITIONAL",
                        "ProductName": "ICICI PRU IPROTECT SMART PLUS",
                        "ProductCode": "T74",
                        "ModeOfPayment": "Monthly",
                        "ModalPremium": "0",
                        "AnnualPremium": "0",
                        "Term": self._convert_to_int_string(tracker.get_slot("term"), "0"),
                        "DeathBenefit": self._convert_to_int_string(tracker.get_slot("sum_assured"), "0"),
                        "PremiumPaymentTerm": str(tracker.get_slot("ppt")) if tracker.get_slot("ppt") else "0",
                        "GstWaiver": "No",
                        "Tobacco": "1" if str(tracker.get_slot("tobacco")).lower() == "yes" else "0",
                        "SalesChannel": "0",
                        "PremiumPaymentOption": "Limited Pay",
                        "RiderDetails": {
                            "Rider": [
                                {
                                    "Name": "ADBW",
                                    "SA": "1000000",
                                    "Term": "30",
                                    "RiderOption": "",
                                    "Percentage": "0",
                                    "RiderPPT": "15"
                                }
                            ]  
                        },
                        "LifeCoverOption": "Life Plus",
                        "DeathBenefitOption": "Lump-Sum",
                        "LumpsumPercentage": "0",
                        "IPSDiscount": "True",
                        "Occupation": "SPVT",
                        "ApplicationNumber": "",
                        "PayoutTerm": "0",
                        "POSFlag": "No"
                    }
                }
            }
        }
        
        # Add additional riders if provided
        riders = tracker.get_slot("rider_name")
        rider_sa = tracker.get_slot("rider_sa")
        term = self._convert_to_int_string(tracker.get_slot("term"), "30")
        ppt = str(tracker.get_slot("ppt")) if tracker.get_slot("ppt") else "15"
        
        if riders and rider_sa:
            for i, r in enumerate(riders):
                data["Root"]["ProductDetails"]["Product"]["RiderDetails"]["Rider"].append({
                    "Name": r,
                    "SA": str(rider_sa[i]) if i < len(rider_sa) and rider_sa[i] else "0",
                    "Term": term,
                    "RiderOption": tracker.get_slot("rider_option") or "",
                    "Percentage": "0",
                    "RiderPPT": ppt
                })
        
        # Call API
        try:
            token = get_cached_token()
            
            print("\n" + "="*80)
            print("API CALL DEBUG INFO")
            print("="*80)
            print(f"\nTOKEN: {token}")
            print(f"\nPAYLOAD (sent to API):")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("\n" + "-"*80)
            
            result = call_main_api(API_URL, token, data)
            
            print(f"\nRESPONSE (received from API):")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"\n❌ API CALL ERROR: {str(e)}\n")
            dispatcher.utter_message(f"❌ Failed to get premium: {str(e)}")
            return [SlotSet("awaiting_premium_confirmation", False)]
        
        # Handle API response
        if isinstance(result, dict):
            error_code = result.get("ErrorCode", "")
            error_msg = result.get("ErrorMessage", "")
            
            is_success = (error_code == "E00" and error_msg == "Success")
            
            if error_code and not is_success:
                dispatcher.utter_message(
                    text=f"Response from API:Unable to generate quotation (Error {error_code}): {error_msg or 'Unknown error'}"
                )
                return [SlotSet("awaiting_premium_confirmation", False)]
            
            if "PremiumSummary" not in result:
                error_msg = result.get("ErrorMessage", "Quotation received, but premium information is missing.")
                dispatcher.utter_message(f"❌ {error_msg}")
                return [SlotSet("awaiting_premium_confirmation", False)]
        
        # Extract and display premium
        try:
            premium = result["PremiumSummary"]["TotalFirstPremium"]
        except (KeyError, TypeError):
            error_msg = result.get("ErrorMessage", "Quotation received, but premium key is missing.") if isinstance(result, dict) else "Quotation received, but premium key is missing."
            dispatcher.utter_message(f"❌ {error_msg}")
            return [SlotSet("awaiting_premium_confirmation", False)]
        
        policy_term = data["Root"]["ProductDetails"]["Product"]["Term"]
        ppt = data["Root"]["ProductDetails"]["Product"]["PremiumPaymentTerm"]
        sum_assured = data["Root"]["ProductDetails"]["Product"]["DeathBenefit"]
        
        dispatcher.utter_message(
            text=(
                f"Quotation Summary: Total Premium (with tax): ₹{premium} per year\n"
                f"Coverage Summary\n"
                f"- Sum Assured: ₹{sum_assured}\n"
                f"- Policy Term: {policy_term} years\n"
                f"- Premium Payment Term (PPT): {ppt} years\n\n"
            )
        )
        
        return [SlotSet("awaiting_premium_confirmation", False)]

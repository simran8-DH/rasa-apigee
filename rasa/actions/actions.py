"""
Insurance Quotation Bot - Custom Actions
This file contains all the custom actions that the bot performs when collecting quotation details.
"""

import re
import json
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Action, Tracker, FormValidationAction
from typing import Any, Dict, List
from actions.api_utils_noED import get_cached_token, call_main_api
from rasa_sdk.types import DomainDict
from actions.properties import API_URL

class ActionActivateQuotationForm(Action):
    """
    This action is called when the user asks for a quotation.
    It simply shows a message asking the user to provide all their details.
    The user can provide all details in one message or answer one by one.
    """
    
    def name(self) -> str:
        return "action_activate_quotation_form"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[str, Any]]:
        
        message = (
            "Great! I'll help you get a quotation. Please provide me with the following details:\n\n"
            "• **Name** (First and Last name)\n"
            "• **Date of Birth** (e.g., 1987/04/06 or 1987 04 june)\n"
            "• **Gender** (Male/Female)\n"
            "• **Marital Status** (Married/Single)\n"
            "• **Tobacco consumption** (Yes/No)\n"
            "• **Sum Assured** (e.g., 5000000)\n"
            "• **Policy Term** (e.g., 20 years)\n"
            "• **Premium Payment Term (PPT)** (e.g., 10 years)\n\n"
            "You can provide all these details in a single message or can chat\n"
        )
        
        dispatcher.utter_message(text=message)
        return []

class ValidateQuotationForm(FormValidationAction):
    """
    This class validates all the information the user provides.
    When the user types something, Rasa calls these validation methods to check and clean the data.
    """

    def name(self):
        return "validate_quotation_form"

    def extract_entities_from_message(self, tracker):
        """
        This method tries to find all information from the user's message.
        First, it checks if Rasa's NLU (Natural Language Understanding) found any entities.
        If not, it uses regex patterns to search the message text directly.
        """
        latest_message = tracker.latest_message
        entities = latest_message.get("entities", [])
        extracted = {}
        
        # Step 1: Get entities that Rasa NLU already found (from regex patterns in nlu.yml)
        for entity in entities:
            entity_name = entity.get("entity")
            entity_value = entity.get("value")
            if entity_name and entity_value:
                extracted[entity_name] = entity_value
        
        # Step 2: If NLU missed something, search the message text directly using regex
        text = latest_message.get("text", "").lower()
        full_text = latest_message.get("text", "")
        
        # Extract names if not found by NLU
        # Look for pattern like "John Doe" (two words at the start)
        if "first_name" not in extracted or "last_name" not in extracted:
            text_for_names = full_text
            # If there's a comma, names are usually before the first comma
            if ',' in text_for_names:
                text_for_names = text_for_names.split(',')[0]
            
            # Match two consecutive words (regex handles case automatically)
            name_pattern = r'^([a-zA-Z]+)\s+([a-zA-Z]+)\b'
            name_match = re.search(name_pattern, text_for_names)
            if name_match:
                if "first_name" not in extracted:
                    extracted["first_name"] = name_match.group(1).capitalize()
                if "last_name" not in extracted:
                    extracted["last_name"] = name_match.group(2).capitalize()
        
        # Extract Date of Birth - try different date formats
        if "dob_quotation" not in extracted:
            dob_patterns = [
                r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
                r'\b(\d{4})\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
                r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b',
            ]
            for pattern in dob_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 3:
                        if match.group(3).isdigit():
                            # Format: YYYY/MM/DD
                            extracted["dob_quotation"] = f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                        else:
                            # Format: YYYY DD Month
                            month_num = self._month_to_num(match.group(3))
                            extracted["dob_quotation"] = f"{match.group(1)}-{month_num:02d}-{int(match.group(2)):02d}"
                    break
        
        # Extract gender - look for "male" or "female" keywords
        if "gender" not in extracted:
            if re.search(r'\b(male|m)\b', text):
                extracted["gender"] = "Male"
            elif re.search(r'\b(female|f)\b', text):
                extracted["gender"] = "Female"
        
        # Extract marital status - look for "married" or "single"
        if "marital_status" not in extracted:
            if re.search(r'\b(married|m)\b', text):
                extracted["marital_status"] = "Married"
            elif re.search(r'\b(single|s)\b', text):
                extracted["marital_status"] = "Single"
        
        # Extract tobacco consumption - look for yes/no patterns
        if "tobacco" not in extracted:
            if re.search(r',\s*(no|n)\s*,', text) or re.search(r'^no\s*,', text) or re.search(r',\s*no$', text):
                extracted["tobacco"] = "No"
            elif re.search(r',\s*(yes|y)\s*,', text) or re.search(r'^yes\s*,', text) or re.search(r',\s*yes$', text):
                extracted["tobacco"] = "Yes"
            elif re.search(r'\b(no|don\'t|dont|doesn\'t|does not|do not)\s+tobacco', text):
                extracted["tobacco"] = "No"
            elif re.search(r'\b(yes|do)\s+tobacco', text):
                extracted["tobacco"] = "Yes"
        
        # Extract sum assured - look for large numbers (6-12 digits, minimum 5 lakhs)
        if "sum_assured" not in extracted:
            sa_pattern = r'\b(\d{6,12})\b'
            sa_matches = re.findall(sa_pattern, full_text)
            if sa_matches:
                for match in reversed(sa_matches):
                    num = int(match)
                    if 500000 <= num <= 999999999999:
                        extracted["sum_assured"] = match
                        break
        
        # Extract policy term - ONLY from comma-separated input (all details at once)
        # NEVER extract term from single number inputs - let validate_term handle it
        if "term" not in extracted:
            # Only extract if we have comma-separated input with 3+ parts
            if ',' in full_text and len(full_text.split(',')) >= 3:
                parts = full_text.split(',')
                for part in parts:
                    part_stripped = part.strip()
                    # Skip dates
                    if re.search(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', part_stripped):
                        continue
                    # Skip large numbers (sum_assured)
                    if re.search(r'\d{6,}', part_stripped):
                        continue
                    # Look for small numbers (5-40) that could be term
                    numbers = re.findall(r'\b(\d{1,2})\b', part_stripped)
                    for num_str in numbers:
                        num = int(num_str)
                        if 5 <= num <= 40:
                            extracted["term"] = str(num)
                            break
                    if "term" in extracted:
                        break
        
        # Extract Premium Payment Term (PPT) - ONLY from comma-separated input (all details at once)
        # NEVER extract PPT from single number inputs - let validate_ppt handle it
        if "ppt" not in extracted:
            # Only extract if we have comma-separated input with 3+ parts
            if ',' in full_text and len(full_text.split(',')) >= 3:
                # In comma-separated input, PPT is usually the last small number
                parts = full_text.split(',')
                for part in reversed(parts):
                    numbers = re.findall(r'\b(\d{1,2})\b', part.strip())
                    for num_str in numbers:
                        num = int(num_str)
                        if 1 <= num <= 40:
                            extracted["ppt"] = str(num)
                            break
                    if "ppt" in extracted:
                        break
        
        return extracted

    def extract_all_slots_from_message(self, tracker):
        """
        This method checks if the user provided ALL details in a single message.
        If yes, it extracts all of them at once so the form doesn't ask again.
        CRITICAL: Never overwrites slots that already have values (when answering one by one).
        """
        latest_message = tracker.latest_message
        full_text = latest_message.get("text", "")
        
        # Check if user provided comma-separated values (like "John Doe, 1987-04-06, male, ...")
        has_commas = ',' in full_text
        
        # Get all entities found in the message
        entities = self.extract_entities_from_message(tracker)
        slot_values = {}
        
        # Count how many different pieces of information we found
        entity_count = sum(1 for key in ["first_name", "last_name", "dob_quotation", "gender", 
                                        "marital_status", "tobacco", "sum_assured", "term", "ppt"] 
                          if key in entities)
        
        # If user provided 2+ pieces of info OR used commas, they likely gave everything at once
        if has_commas or entity_count >= 2:
            # CRITICAL: Only set slots that are currently None/empty
            # Never overwrite slots that already have values (user answered one by one)
            
            if "first_name" in entities and not tracker.get_slot("first_name"):
                slot_values["first_name"] = re.sub(r'[^a-zA-Z\s-]', '', str(entities["first_name"])).strip()
            if "last_name" in entities and not tracker.get_slot("last_name"):
                slot_values["last_name"] = re.sub(r'[^a-zA-Z\s-]', '', str(entities["last_name"])).strip()
            
            if "dob_quotation" in entities and not tracker.get_slot("dob_quotation"):
                dob = str(entities["dob_quotation"])
                if ',' in dob:
                    dob = dob.split(',')[0].strip()
                date_match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', dob)
                if date_match:
                    slot_values["dob_quotation"] = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            
            if "gender" in entities and not tracker.get_slot("gender"):
                gender = str(entities["gender"]).lower()
                if ',' in gender:
                    gender = gender.split(',')[0].strip()
                slot_values["gender"] = "Male" if gender in ["male", "m"] else "Female" if gender in ["female", "f"] else gender.capitalize()
            
            if "marital_status" in entities and not tracker.get_slot("marital_status"):
                status = str(entities["marital_status"]).lower()
                if ',' in status:
                    status = status.split(',')[0].strip()
                slot_values["marital_status"] = "Married" if status in ["married", "m"] else "Single" if status in ["single", "s"] else status.capitalize()
            
            if "tobacco" in entities and not tracker.get_slot("tobacco"):
                tobacco_val = str(entities["tobacco"]).lower()
                if ',' in tobacco_val:
                    tobacco_val = tobacco_val.split(',')[0].strip()
                slot_values["tobacco"] = "Yes" if tobacco_val in ["yes", "y", "do", "does"] else "No" if tobacco_val in ["no", "n", "don't", "dont"] else tobacco_val
            
            if "sum_assured" in entities and not tracker.get_slot("sum_assured"):
                sa_str = str(entities["sum_assured"])
                if ',' in sa_str:
                    sa_str = sa_str.split(',')[0].strip()
                numbers = re.findall(r'\d+', sa_str)
                if numbers:
                    sa_value = float(''.join(numbers))
                    if sa_value >= 500000:
                        slot_values["sum_assured"] = sa_value
            
            # Only set term if it's currently None/empty
            if "term" in entities and not tracker.get_slot("term"):
                term_str = str(entities["term"])
                if ',' in term_str:
                    term_str = term_str.split(',')[0].strip()
                numbers = re.findall(r'\d+', term_str)
                if numbers:
                    term_value = int(float(numbers[0]))
                    if 5 <= term_value <= 40:
                        slot_values["term"] = term_value
            
            # Only set PPT if it's currently None/empty
            if "ppt" in entities and not tracker.get_slot("ppt"):
                ppt_val = str(entities["ppt"])
                if ',' in ppt_val:
                    ppt_val = ppt_val.split(',')[0].strip()
                numbers = re.findall(r'\d+', ppt_val)
                if numbers:
                    slot_values["ppt"] = numbers[0]
                elif "annually" in ppt_val.lower() or "yearly" in ppt_val.lower():
                    slot_values["ppt"] = "Annually"
        
        return slot_values

    def validate_first_name(self, value, dispatcher, tracker, domain):
        """
        This method is called when Rasa needs to validate the first name.
        It checks if the user provided all details at once, or just the first name.
        If user provided full name like "John Doe", it splits it into first and last name.
        """
        # Step 1: Check if user provided ALL details in one message (only if there are commas)
        latest_message = tracker.latest_message
        full_text = latest_message.get("text", "")
        if ',' in full_text:
            all_slots = self.extract_all_slots_from_message(tracker)
            if all_slots:
                return all_slots
        
        # Step 2: Get entities found by NLU
        entities = self.extract_entities_from_message(tracker)
        
        # Step 3: If both first and last name found, return both
        if "first_name" in entities and "last_name" in entities:
            first_name = re.sub(r'[^a-zA-Z\s-]', '', str(entities["first_name"])).strip()
            last_name = re.sub(r'[^a-zA-Z\s-]', '', str(entities["last_name"])).strip()
            if first_name and last_name:
                return {"first_name": first_name, "last_name": last_name}
        
        # Step 4: If only first name found by NLU, use it
        if "first_name" in entities:
            cleaned = re.sub(r'[^a-zA-Z\s-]', '', str(entities["first_name"])).strip()
            if cleaned:
                return {"first_name": cleaned}
        
        # Step 5: If value has space, it might be full name - split it
        if value and isinstance(value, str) and ' ' in value.strip():
            name_part = value.split(',')[0].strip() if ',' in value else value.strip()
            name_parts = name_part.split()
            if len(name_parts) >= 2:
                # Two words = first name and last name
                first_name = re.sub(r'[^a-zA-Z\s-]', '', name_parts[0]).strip()
                last_name = re.sub(r'[^a-zA-Z\s-]', '', name_parts[1]).strip()
                if first_name and last_name:
                    return {"first_name": first_name, "last_name": last_name}
            elif len(name_parts) == 1:
                # One word = just first name
                first_name = re.sub(r'[^a-zA-Z\s-]', '', name_parts[0]).strip()
                if first_name:
                    return {"first_name": first_name}
        
        # Step 6: Clean and return the value as first name
        if value:
            cleaned_value = re.sub(r'[^a-zA-Z\s-]', '', str(value)).strip()
            if cleaned_value:
                return {"first_name": cleaned_value}
        
        return {"first_name": value}

    def validate_last_name(self, value, dispatcher, tracker, domain):
        """
        This method validates the last name.
        If last name was already set (from first_name validation), it keeps that.
        Otherwise, it cleans and validates the provided value.
        """
        entities = self.extract_entities_from_message(tracker)
        
        # If NLU found last name, use it
        if "last_name" in entities:
            last_name = re.sub(r'[^a-zA-Z\s-]', '', str(entities["last_name"])).strip()
            if last_name:
                return {"last_name": last_name}
        
        # If last name was already set (from first_name validation), keep it
        existing_last_name = tracker.get_slot("last_name")
        if existing_last_name:
            cleaned = re.sub(r'[^a-zA-Z\s-]', '', str(existing_last_name)).strip()
            if cleaned:
                return {"last_name": cleaned}
        
        # Clean and return the provided value
        if value:
            value_str = str(value).split(',')[0].strip() if ',' in str(value) else str(value)
            cleaned_value = re.sub(r'[^a-zA-Z\s-]', '', value_str).strip()
            if cleaned_value:
                return {"last_name": cleaned_value}
        
        return {"last_name": value}

    def validate_dob_quotation(self, value, dispatcher, tracker, domain):
        """
        This method validates the date of birth.
        It accepts dates in formats like: 1987/04/06, 1987-04-06, 1987 04 june, etc.
        It converts everything to YYYY-MM-DD format for the API.
        """
        entities = self.extract_entities_from_message(tracker)
        latest_message = tracker.latest_message
        full_text = latest_message.get("text", "")
        
        # Search the full message text for date patterns
        dob = None
        dob_patterns = [
            r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
            r'\b(\d{4})\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
            r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b',
        ]
        
        for pattern in dob_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 3:
                    if match.group(3).isdigit():
                        # Format: YYYY/MM/DD
                        dob = f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                    else:
                        # Format: YYYY DD Month
                        month_num = self._month_to_num(match.group(3))
                        dob = f"{match.group(1)}-{month_num:02d}-{int(match.group(2)):02d}"
                break
        
        # If found in entities, use that
        if "dob_quotation" in entities and not dob:
            dob = str(entities["dob_quotation"])
        
        # If still no dob found, use the value provided
        if not dob and value:
            dob = str(value)
        
        # Clean DOB - extract only date pattern, stop at comma
        if dob and isinstance(dob, str):
            if ',' in dob:
                dob = dob.split(',')[0].strip()
            # Extract date pattern
            date_match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', dob)
            if date_match:
                dob = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            elif not re.match(r'\d{4}-\d{2}-\d{2}', dob):
                # Try natural language dates like "1987 04 june"
                date_patterns = [
                    (r'(\d{4})\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', 
                     lambda m: f"{m.group(1)}-{self._month_to_num(m.group(3)):02d}-{int(m.group(2)):02d}"),
                    (r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})',
                     lambda m: f"{m.group(3)}-{self._month_to_num(m.group(2)):02d}-{int(m.group(1)):02d}"),
                ]
                for pattern, converter in date_patterns:
                    match = re.search(pattern, dob, re.IGNORECASE)
                    if match:
                        dob = converter(match)
                        break
        
        # Only return if we found a valid date (YYYY-MM-DD format)
        if dob and re.match(r'\d{4}-\d{2}-\d{2}', dob):
            return {"dob_quotation": dob}
        
        return {"dob_quotation": value}

    def _month_to_num(self, month_str):
        """
        Helper method: Converts month name (like "january" or "jan") to number (1-12).
        Used when user types dates like "1987 04 june".
        """
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

    def validate_gender(self, value, dispatcher, tracker, domain):
        """
        Validates gender. Accepts "male", "m", "female", "f".
        Returns "Male" or "Female" in proper format.
        """
        entities = self.extract_entities_from_message(tracker)
        if "gender" in entities:
            gender = str(entities["gender"]).lower()
            if ',' in gender:
                gender = gender.split(',')[0].strip()
            if gender in ["male", "m"]:
                return {"gender": "Male"}
            elif gender in ["female", "f"]:
                return {"gender": "Female"}
            return {"gender": str(entities["gender"]).capitalize()}
        
        if value:
            cleaned_value = str(value).split(',')[0].strip().lower()
            if cleaned_value in ["male", "m"]:
                return {"gender": "Male"}
            elif cleaned_value in ["female", "f"]:
                return {"gender": "Female"}
            return {"gender": str(value).split(',')[0].strip().capitalize()}
        
        return {"gender": value}

    def validate_marital_status(self, value, dispatcher, tracker, domain):
        """
        Validates marital status. Accepts "married", "m", "single", "s".
        Returns "Married" or "Single" in proper format.
        """
        entities = self.extract_entities_from_message(tracker)
        if "marital_status" in entities:
            status = str(entities["marital_status"]).lower()
            if ',' in status:
                status = status.split(',')[0].strip()
            if status in ["married", "m"]:
                return {"marital_status": "Married"}
            elif status in ["single", "s"]:
                return {"marital_status": "Single"}
            return {"marital_status": str(entities["marital_status"]).capitalize()}
        
        if value:
            cleaned_value = str(value).split(',')[0].strip().capitalize()
            if cleaned_value in ["Married", "Single", "Divorced", "Widowed"]:
                return {"marital_status": cleaned_value}
        
        return {"marital_status": value}

    def validate_tobacco(self, value, dispatcher, tracker, domain):
        """
        Validates tobacco consumption. Accepts "yes", "y", "no", "n", "don't", etc.
        Returns "Yes" or "No" in proper format.
        """
        entities = self.extract_entities_from_message(tracker)
        if "tobacco" in entities:
            tobacco_val = str(entities["tobacco"]).lower()
            if ',' in tobacco_val:
                tobacco_val = tobacco_val.split(',')[0].strip()
            if tobacco_val in ["yes", "y", "do", "does"]:
                return {"tobacco": "Yes"}
            elif tobacco_val in ["no", "n", "don't", "dont", "doesn't", "does not", "do not"]:
                return {"tobacco": "No"}
            return {"tobacco": str(entities["tobacco"])}
        
        if value:
            cleaned_value = str(value).split(',')[0].strip().lower()
            if cleaned_value in ["yes", "y", "do", "does"]:
                return {"tobacco": "Yes"}
            elif cleaned_value in ["no", "n", "don't", "dont", "doesn't", "does not", "do not"]:
                return {"tobacco": "No"}
            return {"tobacco": str(value).split(',')[0].strip()}
        
        return {"tobacco": value}

    def validate_sum_assured(self, value, dispatcher, tracker, domain):
        """
        Validates sum assured amount. Minimum is 5 lakhs (500000).
        Extracts numbers from the input and validates the amount.
        """
        entities = self.extract_entities_from_message(tracker)
        
        # Helper function to extract and validate sum assured
        def extract_sum_assured(val_str):
            if ',' in val_str:
                val_str = val_str.split(',')[0].strip()
            numbers = re.findall(r'\d+', val_str)
            if numbers:
                try:
                    sa_value = float(''.join(numbers))
                    if sa_value < 500000:
                        dispatcher.utter_message("Minimum sum assured is 5 lakhs.")
                        return None
                    return sa_value
                except (ValueError, TypeError):
                    pass
            return None
        
        if "sum_assured" in entities:
            sa_value = extract_sum_assured(str(entities["sum_assured"]))
            if sa_value is not None:
                return {"sum_assured": sa_value}
        
        if value:
            sa_value = extract_sum_assured(str(value))
            if sa_value is not None:
                return {"sum_assured": sa_value}
            return {"sum_assured": None}
        
        return {"sum_assured": value}

    def validate_term(self, value, dispatcher, tracker, domain):
        """
        Validates policy term. Must be between 5 and 40 years.
        Returns as integer (not float) to avoid API issues.
        """
        # Get requested slot - if form is asking for PPT, don't process term value
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "ppt":
            # Form is asking for PPT, don't change term
            existing_term = tracker.get_slot("term")
            return {"term": existing_term} if existing_term is not None else {}
        
        # Process value only if form is asking for term
        if value:
            try:
                numbers = re.findall(r'\d+', str(value))
                if numbers:
                    term_value = int(numbers[0])
                    if 5 <= term_value <= 40:
                        return {"term": term_value}
                    else:
                        dispatcher.utter_message("Term must be between 5 and 40 years.")
                        return {"term": None}
            except (ValueError, TypeError):
                pass
        
        existing_term = tracker.get_slot("term")
        if existing_term is not None:
            return {"term": existing_term}
        
        return {"term": value}

    def validate_ppt(self, value, dispatcher, tracker, domain):
        """
        Validates Premium Payment Term (PPT).
        Accepts numbers (like "10") or keywords (like "annually", "monthly").
        """
        # Get requested slot - if form is asking for term, don't process PPT value
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "term":
            # Form is asking for term, don't change PPT
            existing_ppt = tracker.get_slot("ppt")
            return {"ppt": existing_ppt} if existing_ppt is not None else {}
        
        # Process value only if form is asking for PPT
        if value:
            value_str = str(value).lower().strip()
            if "annually" in value_str or "yearly" in value_str:
                return {"ppt": "Annually"}
            elif "monthly" in value_str:
                return {"ppt": "Monthly"}
            elif "quarterly" in value_str:
                return {"ppt": "Quarterly"}
            else:
                try:
                    numbers = re.findall(r'\d+', str(value))
                    if numbers:
                        ppt_value = int(numbers[0])
                        if 1 <= ppt_value <= 40:
                            return {"ppt": str(ppt_value)}
                        else:
                            dispatcher.utter_message("PPT must be between 1 and 40 years.")
                            return {"ppt": None}
                except (ValueError, TypeError):
                    pass
        
        existing_ppt = tracker.get_slot("ppt")
        if existing_ppt:
            return {"ppt": existing_ppt}
        
        return {"ppt": value}

class ActionStopPremium(Action):
    """
    This action is called when the user says "no" or "stop" to premium calculation.
    It simply tells the user that the process is stopped.
    """
    
    def name(self) -> str:
        return "action_stop_premium"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[str, Any]]:
        
        dispatcher.utter_message(text="Okay, I've stopped the premium calculation. If you need a quotation later, just let me know!")
        return [SlotSet("awaiting_premium_confirmation", False)]


class ActionSubmitQuotationForm(Action):
    """
    This action is called when the form has collected all required information.
    It shows a summary of what the user provided and asks if they want to proceed
    to calculate the premium.
    """

    def name(self) -> str:
        return "action_submit_quotation_form"

    def run(self, dispatcher, tracker, domain):
        product = "ICICI PRU IPROTECT SMART PLUS"
        mode = "Annually"

        # Show summary of collected information
        dispatcher.utter_message(text="*Quotation Summary*")
        dispatcher.utter_message(
            text=(
                f"*Product:* {product}\n"
                f"*Sum Assured:* {tracker.get_slot('sum_assured')}\n"
                f"*Term:* {tracker.get_slot('term')} years\n"
                f"*Tobacco:* {tracker.get_slot('tobacco')}\n"
                f"*Mode:* {mode}"
            )
        )
        dispatcher.utter_message(text="*Should I proceed to get your premium?* (proceed to continue,stop to cancel)")

        # Set flag to indicate we're waiting for user's confirmation
        return [SlotSet("awaiting_premium_confirmation", True)]


class ActionCallPremiumApi(Action):
    """
    This is the main action that calls the external API to calculate the premium.
    It collects all the information from slots, cleans it, formats it for the API,
    makes the API call, and then displays the result to the user.
    """

    def name(self) -> str:
        return "action_call_premium_api"
    
    def _convert_to_int_string(self, value, default="0"):
        """
        Helper method: Converts any value (int, float, string) to an integer string.
        The API requires integer strings, not floats, so this prevents errors like "5.0" being invalid.
        """
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
        return default

    def run(self, dispatcher, tracker, domain):
        # Step 1: Collect and clean all user inputs from slots
        dob = tracker.get_slot("dob_quotation")
        if dob:
            dob = dob.replace("/", "-").strip()
        
        first_name = tracker.get_slot("first_name")
        last_name = tracker.get_slot("last_name")
        if first_name:
            first_name = re.sub(r'[^a-zA-Z\s-]', '', str(first_name)).strip()
        if last_name:
            last_name = re.sub(r'[^a-zA-Z\s-]', '', str(last_name)).strip()
        
        marital_status = tracker.get_slot("marital_status")
        if marital_status and ',' in str(marital_status):
            marital_status = str(marital_status).split(',')[0].strip()
        
        gender = tracker.get_slot("gender")
        if gender and ',' in str(gender):
            gender = str(gender).split(',')[0].strip()

        # Step 2: Build the API request payload (data structure the API expects)
        data = {
            "Root": {
                "FirstName": first_name or "",
                "LastName": last_name or "",
                "DateOfBirth": dob,
                "Gender": gender or "",
                "MaritalStatus": marital_status or "",
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
                        "ModeOfPayment": "Annually",
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

        # Step 3: Add any additional riders if user provided them
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

        # Step 4: Call the API
        try:
            token = get_cached_token()
            
            # Print token, payload, and response for debugging
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

        # Step 5: Handle API response - check for errors
        if isinstance(result, dict):
            error_code = result.get("ErrorCode", "")
            error_msg = result.get("ErrorMessage", "")
            
            # E00 with "Success" means success, not an error
            is_success = (error_code == "E00" and error_msg == "Success")
            
            # If there's an error code and it's not success, show error message
            if error_code and not is_success:
                dispatcher.utter_message(
                    text=f"Unable to generate quotation (Error {error_code}): {error_msg or 'Unknown error'}"
                )
                return [SlotSet("awaiting_premium_confirmation", False)]
            
            # Check if premium information exists in response
            if "PremiumSummary" not in result:
                error_msg = result.get("ErrorMessage", "Quotation received, but premium information is missing.")
                dispatcher.utter_message(f"❌ {error_msg}")
                return [SlotSet("awaiting_premium_confirmation", False)]

        # Step 6: Extract and display the premium
        try:
            premium = result["PremiumSummary"]["TotalFirstPremium"]
        except (KeyError, TypeError):
            error_msg = result.get("ErrorMessage", "Quotation received, but premium key is missing.") if isinstance(result, dict) else "Quotation received, but premium key is missing."
            dispatcher.utter_message(f"❌ {error_msg}")
            return [SlotSet("awaiting_premium_confirmation", False)]
        
        policy_term = data["Root"]["ProductDetails"]["Product"]["Term"]
        ppt = data["Root"]["ProductDetails"]["Product"]["PremiumPaymentTerm"]
        sum_assured = data["Root"]["ProductDetails"]["Product"]["DeathBenefit"]

        # Step 7: Show the final premium result to user
        dispatcher.utter_message(
            text=(
                f"Quotation Summary\n\n"
                f"Total Premium (with tax): ₹{premium} per year\n\n"
                f"Coverage Summary\n"
                f"- Sum Assured: ₹{sum_assured}\n"
                f"- Policy Term: {policy_term} years\n"
                f"- Premium Payment Term (PPT): {ppt} years\n\n"
            )
        )

        return [SlotSet("awaiting_premium_confirmation", False)]

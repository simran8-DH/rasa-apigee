# """
# Insurance Quotation Bot - Custom Actions
# This file contains all the custom actions that the bot performs when collecting quotation details.
# """

# import re
# import json
# from rasa_sdk.events import SlotSet, ActiveLoop
# from rasa_sdk.executor import CollectingDispatcher
# from rasa_sdk import Action, Tracker, FormValidationAction
# from typing import Any, Dict, List
# from actions.api_utils_noED import get_cached_token, call_main_api
# from rasa_sdk.types import DomainDict
# from actions.properties import API_URL

# class ActionActivateQuotationForm(Action):
#     """
#     This action is called when the user asks for a quotation.
#     If all details are already collected, it directly shows the summary.
#     Otherwise, it shows instructions to collect details.
#     """
    
#     def name(self) -> str:
#         return "action_activate_quotation_form"
    
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: DomainDict) -> List[Dict[str, Any]]:
        
#         # Check if all required slots are already filled
#         required_slots = ["first_name", "last_name", "dob_quotation", "gender", 
#                          "marital_status", "tobacco", "sum_assured", "term", "ppt"]
        
#         all_filled = all(tracker.get_slot(slot) is not None and tracker.get_slot(slot) != "" 
#                         for slot in required_slots)
        
#         # If all slots are filled, directly show summary (skip form)
#         if all_filled:
#             product = "ICICI PRU IPROTECT SMART PLUS"
#             mode = "Annually"
#             dispatcher.utter_message(
#                 text=(
#                     "*Quotation Summary*\n"
#                     f"*Product:* {product}\n"
#                     f"*Sum Assured:* {tracker.get_slot('sum_assured')}\n"
#                     f"*Term:* {tracker.get_slot('term')} years\n"
#                     f"*Tobacco:* {tracker.get_slot('tobacco')}\n"
#                     f"*Mode:* {mode}\n"
#                     "*Should I proceed to get your premium?* (proceed/stop)"
#                 )
#             )
#             # Return ActiveLoop(null) to prevent form from activating, and set confirmation flag
#             return [
#                 ActiveLoop(None),
#                 SlotSet("awaiting_premium_confirmation", True)
#             ]
        
#         # If slots are not filled, show instructions to collect details
#         message = (
#             "Great! I'll help you get a quotation. Please provide me with the following details:\n"
#             "• Name (First and Last name)\n"
#             "• Date of Birth (e.g., 1987/04/06 or 1987 04 june)\n"
#             "• Gender (Male/Female)\n"
#             "• Marital Status (Married/Single)\n"
#             "• Tobacco consumption (Yes/No)\n"
#             "• Policy Term (e.g., 20 years)\n"
#             # "• Premium Payment Term (PPT) (e.g., 10 years)\n"
#             "• Sum Assured (e.g., 5000000)\n"
#             "You can provide all these details in a single comma-separated message or can chat.\n"
#         )
#         dispatcher.utter_message(text=message)
#         return []

# class ValidateQuotationForm(FormValidationAction):
#     """
#     This class validates all the information the user provides.
#     When the user types something, Rasa calls these validation methods to check and clean the data.
#     """

#     def name(self):
#         return "validate_quotation_form"

#     def extract_entities_from_message(self, tracker):
#         """
#         This method tries to find all information from the user's message.
#         First, it checks if Rasa's NLU (Natural Language Understanding) found any entities.
#         If not, it uses regex patterns to search the message text directly.
#         """
#         latest_message = tracker.latest_message
#         entities = latest_message.get("entities", [])
#         extracted = {}
        
#         # Step 1: Get entities that Rasa NLU already found (from regex patterns in nlu.yml)
#         for entity in entities:
#             entity_name = entity.get("entity")
#             entity_value = entity.get("value")
#             if entity_name and entity_value:
#                 extracted[entity_name] = entity_value
        
#         # Step 2: If NLU missed something, search the message text directly using regex
#         full_text = latest_message.get("text", "") or ""
#         # For comma-separated inputs, normalize spaces directly after commas
#         # e.g. ", 10" -> ",10" so that number extraction is consistent
#         full_text = re.sub(r',\s+(\d)', r',\1', full_text)
#         text = full_text.lower()
        
#         # Extract names if not found by NLU
#         # Look for pattern like "John Doe" (two words at the start)
#         if "first_name" not in extracted or "last_name" not in extracted:
#             text_for_names = full_text
#             # If there's a comma, names are usually before the first comma
#             if ',' in text_for_names:
#                 text_for_names = text_for_names.split(',')[0]
            
#             # Match two consecutive words (regex handles case automatically)
#             name_pattern = r'^([a-zA-Z]+)\s+([a-zA-Z]+)\b'
#             name_match = re.search(name_pattern, text_for_names)
#             if name_match:
#                 if "first_name" not in extracted:
#                     extracted["first_name"] = name_match.group(1).capitalize()
#                 if "last_name" not in extracted:
#                     extracted["last_name"] = name_match.group(2).capitalize()
        
#         # Extract Date of Birth - try different date formats
#         if "dob_quotation" not in extracted:
#             dob_patterns = [
#                 r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
#                 r'\b(\d{4})\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
#                 r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b',
#             ]
#             for pattern in dob_patterns:
#                 match = re.search(pattern, full_text, re.IGNORECASE)
#                 if match:
#                     if len(match.groups()) == 3:
#                         if match.group(3).isdigit():
#                             # Format: YYYY/MM/DD
#                             extracted["dob_quotation"] = f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
#                         else:
#                             # Format: YYYY DD Month
#                             month_num = self._month_to_num(match.group(3))
#                             extracted["dob_quotation"] = f"{match.group(1)}-{month_num:02d}-{int(match.group(2)):02d}"
#                     break
        
#         # Extract gender - look for "male" or "female" keywords
#         if "gender" not in extracted:
#             if re.search(r'\b(male|m)\b', text):
#                 extracted["gender"] = "Male"
#             elif re.search(r'\b(female|f)\b', text):
#                 extracted["gender"] = "Female"
        
#         # Extract marital status - look for "married" or "single"
#         if "marital_status" not in extracted:
#             if re.search(r'\b(married|m)\b', text):
#                 extracted["marital_status"] = "Married"
#             elif re.search(r'\b(single|s)\b', text):
#                 extracted["marital_status"] = "Single"
        
#         # Extract tobacco consumption - look for yes/no patterns
#         if "tobacco" not in extracted:
#             if re.search(r',\s*(no|n)\s*,', text) or re.search(r'^no\s*,', text) or re.search(r',\s*no$', text):
#                 extracted["tobacco"] = "No"
#             elif re.search(r',\s*(yes|y)\s*,', text) or re.search(r'^yes\s*,', text) or re.search(r',\s*yes$', text):
#                 extracted["tobacco"] = "Yes"
#             elif re.search(r'\b(no|don\'t|dont|doesn\'t|does not|do not)\s+tobacco', text):
#                 extracted["tobacco"] = "No"
#             elif re.search(r'\b(yes|do)\s+tobacco', text):
#                 extracted["tobacco"] = "Yes"
        
#         # Extract sum assured - look for large numbers (6-12 digits, minimum 5 lakhs)
#         if "sum_assured" not in extracted:
#             sa_pattern = r'\b(\d{6,12})\b'
#             sa_matches = re.findall(sa_pattern, full_text)
#             if sa_matches:
#                 for match in reversed(sa_matches):
#                     num = int(match)
#                     if 500000 <= num <= 999999999999:
#                         extracted["sum_assured"] = match
#                         break
        
#         # Extract policy term - First check for "term" keyword, then position-based
#         if "term" not in extracted:
#             # First, try to find "term" or "policy term" keyword with a number (e.g., "25 term", "25 policy term")
#             # This works even if not comma-separated
#             term_patterns = [
#                 r'\b(\d{1,2})\s*(?:years?)?\s*term\b',  # "25 term" or "25 years term"
#                 r'\b(\d{1,2})\s*policy\s*term\b',  # "25 policy term"
#                 r'term\s*(?:is|of)?\s*(\d{1,2})\s*(?:years?)?\b',  # "term is 25" or "term 25"
#             ]
#             for pattern in term_patterns:
#                 term_match = re.search(pattern, full_text, re.IGNORECASE)
#                 if term_match:
#                     num = int(term_match.group(1))
#                     if 5 <= num <= 40:
#                         extracted["term"] = str(num)
#                         break
            
#             # If not found with keyword, try comma-separated extraction (only if 3+ parts)
#             if "term" not in extracted and ',' in full_text and len(full_text.split(',')) >= 3:
#                 parts = full_text.split(',')
#                 for part in parts:
#                     part_stripped = part.strip()
#                     # Skip dates
#                     if re.search(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', part_stripped):
#                         continue
#                     # Skip large numbers (sum_assured)
#                     if re.search(r'\d{6,}', part_stripped):
#                         continue
#                     # Skip if this part has "ppt" keyword (we're looking for term)
#                     if re.search(r'\bppt\b', part_stripped, re.IGNORECASE):
#                         continue
#                     # Look for small numbers (5-40) that could be term
#                     numbers = re.findall(r'\b(\d{1,2})\b', part_stripped)
#                     for num_str in numbers:
#                         num = int(num_str)
#                         if 5 <= num <= 40:
#                             extracted["term"] = str(num)
#                             break
#                     if "term" in extracted:
#                         break
        
#         # Extract Premium Payment Term (PPT) - First check for "ppt" keyword, then position-based
#         if "ppt" not in extracted:
#             # First, try to find "ppt" keyword with a number (e.g., "5 ppt", "5 years ppt", "12 ppt")
#             # This works even if not comma-separated
#             ppt_patterns = [
#                 r'\b(\d{1,2})\s*ppt\b',  # "12 ppt" (most specific - number directly before ppt)
#                 r'\b(\d{1,2})\s*(?:years?)?\s*ppt\b',  # "5 ppt" or "5 years ppt"
#                 r'ppt\s*(?:is|of)?\s*(\d{1,2})\s*(?:years?)?\b',  # "ppt is 5" or "ppt 5"
#                 r'premium\s*payment\s*term.*?(\d{1,2})\s*(?:years?)?\b',  # "premium payment term 5"
#             ]
#             for pattern in ppt_patterns:
#                 ppt_match = re.search(pattern, full_text, re.IGNORECASE)
#                 if ppt_match:
#                     num = int(ppt_match.group(1))
#                     if 1 <= num <= 40:
#                         extracted["ppt"] = str(num)
#                         break
            
#             # If not found with keyword, try comma-separated extraction (only if 3+ parts)
#             if "ppt" not in extracted and ',' in full_text and len(full_text.split(',')) >= 3:
#                 parts = full_text.split(',')
#                 term_value = extracted.get("term")  # Get term value if already extracted
#                 # In comma-separated input, PPT is usually the last small number (after term)
#                 for part in reversed(parts):
#                     part_stripped = part.strip()
#                     # Skip dates
#                     if re.search(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', part_stripped):
#                         continue
#                     # Skip large numbers (sum_assured)
#                     if re.search(r'\d{6,}', part_stripped):
#                         continue
#                     # Skip if this part has "term" keyword (we're looking for PPT)
#                     if re.search(r'\bterm\b', part_stripped, re.IGNORECASE):
#                         continue
#                     numbers = re.findall(r'\b(\d{1,2})\b', part_stripped)
#                     for num_str in numbers:
#                         num = int(num_str)
#                         if 1 <= num <= 40:
#                             # If term was already extracted and this number is different, it's PPT
#                             if term_value and str(num) != term_value:
#                                 extracted["ppt"] = str(num)
#                                 break
#                             # If term not extracted yet, this could be PPT (last small number)
#                             elif not term_value:
#                                 extracted["ppt"] = str(num)
#                                 break
#                     if "ppt" in extracted:
#                         break
        
#         return extracted

#     def extract_all_slots_from_message(self, tracker):
#         """
#         This method checks if the user provided ALL details in a single message.
#         If yes, it extracts all of them at once so the form doesn't ask again.
#         CRITICAL: Never overwrites slots that already have values (when answering one by one).
#         """
#         latest_message = tracker.latest_message
#         full_text = latest_message.get("text", "")
        
#         # Check if user provided comma-separated values (like "John Doe, 1987-04-06, male, ...")
#         has_commas = ',' in full_text
        
#         # Get all entities found in the message
#         entities = self.extract_entities_from_message(tracker)
#         slot_values = {}
        
#         # Count how many different pieces of information we found
#         entity_count = sum(1 for key in ["first_name", "last_name", "dob_quotation", "gender", 
#                                         "marital_status", "tobacco", "sum_assured", "term", "ppt"] 
#                           if key in entities)
        
#         # If user provided 2+ pieces of info OR used commas, they likely gave everything at once
#         if has_commas or entity_count >= 2:
#             # CRITICAL: Only set slots that are currently None/empty
#             # Never overwrite slots that already have values (user answered one by one)
            
#             if "first_name" in entities and not tracker.get_slot("first_name"):
#                 slot_values["first_name"] = re.sub(r'[^a-zA-Z\s-]', '', str(entities["first_name"])).strip()
#             if "last_name" in entities and not tracker.get_slot("last_name"):
#                 slot_values["last_name"] = re.sub(r'[^a-zA-Z\s-]', '', str(entities["last_name"])).strip()
            
#             if "dob_quotation" in entities and not tracker.get_slot("dob_quotation"):
#                 dob = str(entities["dob_quotation"])
#                 if ',' in dob:
#                     dob = dob.split(',')[0].strip()
#                 date_match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', dob)
#                 if date_match:
#                     slot_values["dob_quotation"] = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            
#             if "gender" in entities and not tracker.get_slot("gender"):
#                 gender = str(entities["gender"]).lower()
#                 if ',' in gender:
#                     gender = gender.split(',')[0].strip()
#                 slot_values["gender"] = "Male" if gender in ["male", "m"] else "Female" if gender in ["female", "f"] else gender.capitalize()
            
#             if "marital_status" in entities and not tracker.get_slot("marital_status"):
#                 status = str(entities["marital_status"]).lower()
#                 if ',' in status:
#                     status = status.split(',')[0].strip()
#                 slot_values["marital_status"] = "Married" if status in ["married", "m"] else "Single" if status in ["single", "s"] else status.capitalize()
            
#             if "tobacco" in entities and not tracker.get_slot("tobacco"):
#                 tobacco_val = str(entities["tobacco"]).lower()
#                 if ',' in tobacco_val:
#                     tobacco_val = tobacco_val.split(',')[0].strip()
#                 slot_values["tobacco"] = "Yes" if tobacco_val in ["yes", "y", "do", "does"] else "No" if tobacco_val in ["no", "n", "don't", "dont"] else tobacco_val
            
#             if "sum_assured" in entities and not tracker.get_slot("sum_assured"):
#                 sa_str = str(entities["sum_assured"])
#                 if ',' in sa_str:
#                     sa_str = sa_str.split(',')[0].strip()
#                 numbers = re.findall(r'\d+', sa_str)
#                 if numbers:
#                     sa_value = float(''.join(numbers))
#                     if sa_value >= 500000:
#                         slot_values["sum_assured"] = sa_value
            
#             # Only set term if it's currently None/empty
#             if "term" in entities and not tracker.get_slot("term"):
#                 term_str = str(entities["term"])
#                 if ',' in term_str:
#                     term_str = term_str.split(',')[0].strip()
#                 numbers = re.findall(r'\d+', term_str)
#                 if numbers:
#                     term_value = int(float(numbers[0]))
#                     if 5 <= term_value <= 40:
#                         slot_values["term"] = term_value
            
#             # Only set PPT if it's currently None/empty
#             if "ppt" in entities and not tracker.get_slot("ppt"):
#                 ppt_val = str(entities["ppt"])
#                 if ',' in ppt_val:
#                     ppt_val = ppt_val.split(',')[0].strip()
#                 # Check for keywords first
#                 if "annually" in ppt_val.lower() or "yearly" in ppt_val.lower():
#                     slot_values["ppt"] = "Annually"
#                 elif "monthly" in ppt_val.lower():
#                     slot_values["ppt"] = "Monthly"
#                 else:
#                     # Extract number from PPT value (handles "12", "12 ppt", "12 years", etc.)
#                     numbers = re.findall(r'\d+', ppt_val)
#                     if numbers:
#                         ppt_num = int(numbers[0])
#                         if 1 <= ppt_num <= 40:
#                             slot_values["ppt"] = str(ppt_num)
        
#         return slot_values

#     def validate_first_name(self, value, dispatcher, tracker, domain):
#         """
#         This method is called when Rasa needs to validate the first name.
#         It checks if the user provided all details at once, or just the first name.
#         If user provided full name like "John Doe", it splits it into first and last name.
#         """
#         # Step 1: Check if user provided ALL details in one message (only if there are commas)
#         latest_message = tracker.latest_message
#         full_text = latest_message.get("text", "")
#         if ',' in full_text:
#             all_slots = self.extract_all_slots_from_message(tracker)
#             if all_slots:
#                 return all_slots
        
#         # Step 2: Get entities found by NLU
#         entities = self.extract_entities_from_message(tracker)
        
#         # Step 3: If both first and last name found, return both
#         if "first_name" in entities and "last_name" in entities:
#             first_name = re.sub(r'[^a-zA-Z\s-]', '', str(entities["first_name"])).strip()
#             last_name = re.sub(r'[^a-zA-Z\s-]', '', str(entities["last_name"])).strip()
#             if first_name and last_name:
#                 return {"first_name": first_name, "last_name": last_name}
        
#         # Step 4: If only first name found by NLU, use it
#         if "first_name" in entities:
#             cleaned = re.sub(r'[^a-zA-Z\s-]', '', str(entities["first_name"])).strip()
#             if cleaned:
#                 return {"first_name": cleaned}
        
#         # Step 5: If value has space, it might be full name - split it
#         if value and isinstance(value, str) and ' ' in value.strip():
#             name_part = value.split(',')[0].strip() if ',' in value else value.strip()
#             name_parts = name_part.split()
#             if len(name_parts) >= 2:
#                 # Two words = first name and last name
#                 first_name = re.sub(r'[^a-zA-Z\s-]', '', name_parts[0]).strip()
#                 last_name = re.sub(r'[^a-zA-Z\s-]', '', name_parts[1]).strip()
#                 if first_name and last_name:
#                     return {"first_name": first_name, "last_name": last_name}
#             elif len(name_parts) == 1:
#                 # One word = just first name
#                 first_name = re.sub(r'[^a-zA-Z\s-]', '', name_parts[0]).strip()
#                 if first_name:
#                     return {"first_name": first_name}
        
#         # Step 6: Clean and return the value as first name
#         if value:
#             cleaned_value = re.sub(r'[^a-zA-Z\s-]', '', str(value)).strip()
#             if cleaned_value:
#                 return {"first_name": cleaned_value}
        
#         return {"first_name": value}

#     def validate_last_name(self, value, dispatcher, tracker, domain):
#         """
#         This method validates the last name.
#         If last name was already set (from first_name validation), it keeps that.
#         Otherwise, it cleans and validates the provided value.
#         """
#         entities = self.extract_entities_from_message(tracker)
        
#         # If NLU found last name, use it
#         if "last_name" in entities:
#             last_name = re.sub(r'[^a-zA-Z\s-]', '', str(entities["last_name"])).strip()
#             if last_name:
#                 return {"last_name": last_name}
        
#         # If last name was already set (from first_name validation), keep it
#         existing_last_name = tracker.get_slot("last_name")
#         if existing_last_name:
#             cleaned = re.sub(r'[^a-zA-Z\s-]', '', str(existing_last_name)).strip()
#             if cleaned:
#                 return {"last_name": cleaned}
        
#         # Clean and return the provided value
#         if value:
#             value_str = str(value).split(',')[0].strip() if ',' in str(value) else str(value)
#             cleaned_value = re.sub(r'[^a-zA-Z\s-]', '', value_str).strip()
#             if cleaned_value:
#                 return {"last_name": cleaned_value}
        
#         return {"last_name": value}

#     def validate_dob_quotation(self, value, dispatcher, tracker, domain):
#         """
#         This method validates the date of birth.
#         It accepts dates in formats like: 1987/04/06, 1987-04-06, 1987 04 june, etc.
#         It converts everything to YYYY-MM-DD format for the API.
#         """
#         entities = self.extract_entities_from_message(tracker)
#         latest_message = tracker.latest_message
#         full_text = latest_message.get("text", "")
        
#         # Search the full message text for date patterns
#         dob = None
#         dob_patterns = [
#             r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
#             r'\b(\d{4})\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
#             r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b',
#         ]
        
#         for pattern in dob_patterns:
#             match = re.search(pattern, full_text, re.IGNORECASE)
#             if match:
#                 if len(match.groups()) == 3:
#                     if match.group(3).isdigit():
#                         # Format: YYYY/MM/DD
#                         dob = f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
#                     else:
#                         # Format: YYYY DD Month
#                         month_num = self._month_to_num(match.group(3))
#                         dob = f"{match.group(1)}-{month_num:02d}-{int(match.group(2)):02d}"
#                 break
        
#         # If found in entities, use that
#         if "dob_quotation" in entities and not dob:
#             dob = str(entities["dob_quotation"])
        
#         # If still no dob found, use the value provided
#         if not dob and value:
#             dob = str(value)
        
#         # Clean DOB - extract only date pattern, stop at comma
#         if dob and isinstance(dob, str):
#             if ',' in dob:
#                 dob = dob.split(',')[0].strip()
#             # Extract date pattern
#             date_match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', dob)
#             if date_match:
#                 dob = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
#             elif not re.match(r'\d{4}-\d{2}-\d{2}', dob):
#                 # Try natural language dates like "1987 04 june"
#                 date_patterns = [
#                     (r'(\d{4})\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', 
#                      lambda m: f"{m.group(1)}-{self._month_to_num(m.group(3)):02d}-{int(m.group(2)):02d}"),
#                     (r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})',
#                      lambda m: f"{m.group(3)}-{self._month_to_num(m.group(2)):02d}-{int(m.group(1)):02d}"),
#                 ]
#                 for pattern, converter in date_patterns:
#                     match = re.search(pattern, dob, re.IGNORECASE)
#                     if match:
#                         dob = converter(match)
#                         break
        
#         # Only return if we found a valid date (YYYY-MM-DD format)
#         if dob and re.match(r'\d{4}-\d{2}-\d{2}', dob):
#             return {"dob_quotation": dob}
        
#         return {"dob_quotation": value}

#     def _month_to_num(self, month_str):
#         """
#         Helper method: Converts month name (like "january" or "jan") to number (1-12).
#         Used when user types dates like "1987 04 june".
#         """
#         months = {
#             'january': 1, 'jan': 1,
#             'february': 2, 'feb': 2,
#             'march': 3, 'mar': 3,
#             'april': 4, 'apr': 4,
#             'may': 5,
#             'june': 6, 'jun': 6,
#             'july': 7, 'jul': 7,
#             'august': 8, 'aug': 8,
#             'september': 9, 'sep': 9,
#             'october': 10, 'oct': 10,
#             'november': 11, 'nov': 11,
#             'december': 12, 'dec': 12
#         }
#         return months.get(month_str.lower(), 1)

#     def validate_gender(self, value, dispatcher, tracker, domain):
#         """
#         Validates gender. Accepts "male", "m", "female", "f".
#         Returns "Male" or "Female" in proper format.
#         """
#         entities = self.extract_entities_from_message(tracker)
#         if "gender" in entities:
#             gender = str(entities["gender"]).lower()
#             if ',' in gender:
#                 gender = gender.split(',')[0].strip()
#             if gender in ["male", "m"]:
#                 return {"gender": "Male"}
#             elif gender in ["female", "f"]:
#                 return {"gender": "Female"}
#             return {"gender": str(entities["gender"]).capitalize()}
        
#         if value:
#             cleaned_value = str(value).split(',')[0].strip().lower()
#             if cleaned_value in ["male", "m"]:
#                 return {"gender": "Male"}
#             elif cleaned_value in ["female", "f"]:
#                 return {"gender": "Female"}
#             return {"gender": str(value).split(',')[0].strip().capitalize()}
        
#         return {"gender": value}

#     def validate_marital_status(self, value, dispatcher, tracker, domain):
#         """
#         Validates marital status. Accepts "married", "m", "single", "s".
#         Returns "Married" or "Single" in proper format.
#         """
#         entities = self.extract_entities_from_message(tracker)
#         if "marital_status" in entities:
#             status = str(entities["marital_status"]).lower()
#             if ',' in status:
#                 status = status.split(',')[0].strip()
#             if status in ["married", "m"]:
#                 return {"marital_status": "Married"}
#             elif status in ["single", "s"]:
#                 return {"marital_status": "Single"}
#             return {"marital_status": str(entities["marital_status"]).capitalize()}
        
#         if value:
#             cleaned_value = str(value).split(',')[0].strip().capitalize()
#             if cleaned_value in ["Married", "Single", "Divorced", "Widowed"]:
#                 return {"marital_status": cleaned_value}
        
#         return {"marital_status": value}

#     def validate_tobacco(self, value, dispatcher, tracker, domain):
#         """
#         Validates tobacco consumption. Accepts "yes", "y", "no", "n", "don't", etc.
#         Returns "Yes" or "No" in proper format.
#         """
#         entities = self.extract_entities_from_message(tracker)
#         if "tobacco" in entities:
#             tobacco_val = str(entities["tobacco"]).lower()
#             if ',' in tobacco_val:
#                 tobacco_val = tobacco_val.split(',')[0].strip()
#             if tobacco_val in ["yes", "y", "do", "does"]:
#                 return {"tobacco": "Yes"}
#             elif tobacco_val in ["no", "n", "don't", "dont", "doesn't", "does not", "do not"]:
#                 return {"tobacco": "No"}
#             return {"tobacco": str(entities["tobacco"])}
        
#         if value:
#             cleaned_value = str(value).split(',')[0].strip().lower()
#             if cleaned_value in ["yes", "y", "do", "does"]:
#                 return {"tobacco": "Yes"}
#             elif cleaned_value in ["no", "n", "don't", "dont", "doesn't", "does not", "do not"]:
#                 return {"tobacco": "No"}
#             return {"tobacco": str(value).split(',')[0].strip()}
        
#         return {"tobacco": value}

#     def validate_sum_assured(self, value, dispatcher, tracker, domain):
#         """
#         Validates sum assured amount. Minimum is 5 lakhs (500000).
#         Extracts numbers from the input and validates the amount.
#         """
#         entities = self.extract_entities_from_message(tracker)
        
#         # Helper function to extract and validate sum assured
#         def extract_sum_assured(val_str):
#             if ',' in val_str:
#                 val_str = val_str.split(',')[0].strip()
#             numbers = re.findall(r'\d+', val_str)
#             if numbers:
#                 try:
#                     sa_value = float(''.join(numbers))
#                     if sa_value < 500000:
#                         dispatcher.utter_message("Minimum sum assured is 5 lakhs.")
#                         return None
#                     return sa_value
#                 except (ValueError, TypeError):
#                     pass
#             return None
        
#         if "sum_assured" in entities:
#             sa_value = extract_sum_assured(str(entities["sum_assured"]))
#             if sa_value is not None:
#                 return {"sum_assured": sa_value}
        
#         if value:
#             sa_value = extract_sum_assured(str(value))
#             if sa_value is not None:
#                 return {"sum_assured": sa_value}
#             return {"sum_assured": None}
        
#         return {"sum_assured": value}

#     def validate_term(self, value, dispatcher, tracker, domain):
#         """
#         Validates policy term. Must be between 5 and 40 years.
#         Returns as integer (not float) to avoid API issues.
#         """
#         # Get requested slot - if form is asking for PPT, don't process term value
#         requested_slot = tracker.get_slot("requested_slot")
#         if requested_slot == "ppt":
#             # Form is asking for PPT, don't change term
#             existing_term = tracker.get_slot("term")
#             return {"term": existing_term} if existing_term is not None else {}
        
#         # Process value only if form is asking for term
#         if value:
#             try:
#                 numbers = re.findall(r'\d+', str(value))
#                 if numbers:
#                     term_value = int(numbers[0])
#                     if 5 <= term_value <= 40:
#                         return {"term": term_value}
#                     else:
#                         dispatcher.utter_message("Term must be between 5 and 40 years.")
#                         return {"term": None}
#             except (ValueError, TypeError):
#                 pass
        
#         existing_term = tracker.get_slot("term")
#         if existing_term is not None:
#             return {"term": existing_term}
        
#         return {"term": value}

#     def validate_ppt(self, value, dispatcher, tracker, domain):
#         """
#         Validates Premium Payment Term (PPT).
#         Accepts numbers (like "10") or keywords (like "annually", "monthly").
#         """
#         # Get requested slot - if form is asking for term, don't process PPT value
#         requested_slot = tracker.get_slot("requested_slot")
#         if requested_slot == "term":
#             # Form is asking for term, don't change PPT
#             existing_ppt = tracker.get_slot("ppt")
#             return {"ppt": existing_ppt} if existing_ppt is not None else {}
        
#         # Process value only if form is asking for PPT
#         if value:
#             value_str = str(value).lower().strip()
#             if "annually" in value_str or "yearly" in value_str:
#                 return {"ppt": "Annually"}
#             elif "monthly" in value_str:
#                 return {"ppt": "Monthly"}
#             elif "quarterly" in value_str:
#                 return {"ppt": "Quarterly"}
#             else:
#                 try:
#                     numbers = re.findall(r'\d+', str(value))
#                     if numbers:
#                         ppt_value = int(numbers[0])
#                         if 1 <= ppt_value <= 40:
#                             return {"ppt": str(ppt_value)}
#                         else:
#                             dispatcher.utter_message("PPT must be between 1 and 40 years.")
#                             return {"ppt": None}
#                 except (ValueError, TypeError):
#                     pass
        
#         existing_ppt = tracker.get_slot("ppt")
#         if existing_ppt:
#             return {"ppt": existing_ppt}
        
#         return {"ppt": value}

# class ActionStopPremium(Action):
#     """
#     This action is called when the user says "no" or "stop" to premium calculation.
#     It simply tells the user that the process is stopped.
#     """
    
#     def name(self) -> str:
#         return "action_stop_premium"
    
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: DomainDict) -> List[Dict[str, Any]]:
        
#         dispatcher.utter_message(text="Okay, I've stopped the premium calculation. If you need a quotation later, just let me know!")
#         return [SlotSet("awaiting_premium_confirmation", False)]


# class ActionSubmitQuotationForm(Action):
#     """
#     This action is called when the form has collected all required information.
#     It shows a summary of what the user provided and asks if they want to proceed
#     to calculate the premium.
#     """

#     def name(self) -> str:
#         return "action_submit_quotation_form"

#     def run(self, dispatcher, tracker, domain):
#         product = "ICICI PRU IPROTECT SMART PLUS"
#         mode = "Annually"

#         dispatcher.utter_message(
#         text=(
#             "*Quotation Summary*\n"
#         f"*Product:* {product}\n"
#         f"*Sum Assured:* {tracker.get_slot('sum_assured')}\n"
#         f"*Term:* {tracker.get_slot('term')} years\n"
#         f"*Tobacco:* {tracker.get_slot('tobacco')}\n"
#         f"*Mode:* {mode}\n"
#         "*Should I proceed to get your premium?* (proceed/stop)"
#     )
# )
#         # Set flag to indicate we're waiting for user's confirmation
#         return [SlotSet("awaiting_premium_confirmation", True)]


# class ActionCallPremiumApi(Action):
#     """
#     This is the main action that calls the external API to calculate the premium.
#     It collects all the information from slots, cleans it, formats it for the API,
#     makes the API call, and then displays the result to the user.
#     """

#     def name(self) -> str:
#         return "action_call_premium_api"
    
#     def _convert_to_int_string(self, value, default="0"):
#         """
#         Helper method: Converts any value (int, float, string) to an integer string.
#         The API requires integer strings, not floats, so this prevents errors like "5.0" being invalid.
#         """
#         if value is None:
#             return default
#         try:
#             if isinstance(value, str):
#                 cleaned = re.sub(r'[^\d.]', '', value)
#                 if cleaned:
#                     return str(int(float(cleaned)))
#             else:
#                 return str(int(float(value)))
#         except (ValueError, TypeError):
#             return default
#         return default

#     def run(self, dispatcher, tracker, domain):
#         # Step 1: Collect and clean all user inputs from slots
#         dob = tracker.get_slot("dob_quotation")
#         if dob:
#             dob = dob.replace("/", "-").strip()
        
#         first_name = tracker.get_slot("first_name")
#         last_name = tracker.get_slot("last_name")
#         if first_name:
#             first_name = re.sub(r'[^a-zA-Z\s-]', '', str(first_name)).strip()
#         if last_name:
#             last_name = re.sub(r'[^a-zA-Z\s-]', '', str(last_name)).strip()
        
#         marital_status = tracker.get_slot("marital_status")
#         if marital_status and ',' in str(marital_status):
#             marital_status = str(marital_status).split(',')[0].strip()
        
#         gender = tracker.get_slot("gender")
#         if gender and ',' in str(gender):
#             gender = str(gender).split(',')[0].strip()

#         # Step 2: Build the API request payload (data structure the API expects)
#         data = {
#             "Root": {
#                 "FirstName": first_name or "",
#                 "LastName": last_name or "",
#                 "DateOfBirth": dob,
#                 "Gender": gender or "",
#                 "MaritalStatus": marital_status or "",
#                 "PolicyholderFName": "",
#                 "PolicyholderLName": "",
#                 "PolicyholderDOB": "",
#                 "PolicyholderGender": "",
#                 "isNRI": "false",
#                 "isPolicyholder": "",
#                 "Staff": "0",
#                 "ProductDetails": {
#                     "Product": {
#                         "ProductType": "TRADITIONAL",
#                         "ProductName": "ICICI PRU IPROTECT SMART PLUS",
#                         "ProductCode": "T74",
#                         "ModeOfPayment": "Annually",
#                         "ModalPremium": "0",
#                         "AnnualPremium": "0",
#                         "Term": self._convert_to_int_string(tracker.get_slot("term"), "0"),
#                         "DeathBenefit": self._convert_to_int_string(tracker.get_slot("sum_assured"), "0"),
#                         "PremiumPaymentTerm": str(tracker.get_slot("ppt")) if tracker.get_slot("ppt") else "0",
#                         "GstWaiver": "No",
#                         "Tobacco": "1" if str(tracker.get_slot("tobacco")).lower() == "yes" else "0",
#                         "SalesChannel": "0",
#                         "PremiumPaymentOption": "Limited Pay",
#                         "RiderDetails": {
#                             "Rider": [
#                                 {
#                                     "Name": "ADBW",
#                                     "SA": "1000000",
#                                     "Term": "30",
#                                     "RiderOption": "",
#                                     "Percentage": "0",
#                                     "RiderPPT": "15"
#                                 }
#                             ]  
#                         },
#                         "LifeCoverOption": "Life Plus",
#                         "DeathBenefitOption": "Lump-Sum",
#                         "LumpsumPercentage": "0",
#                         "IPSDiscount": "True",
#                         "Occupation": "SPVT",
#                         "ApplicationNumber": "",
#                         "PayoutTerm": "0",
#                         "POSFlag": "No"
#                     }
#                 }
#             }
#         }

#         # Step 3: Add any additional riders if user provided them
#         riders = tracker.get_slot("rider_name")
#         rider_sa = tracker.get_slot("rider_sa")
#         term = self._convert_to_int_string(tracker.get_slot("term"), "30")
#         ppt = str(tracker.get_slot("ppt")) if tracker.get_slot("ppt") else "15"

#         if riders and rider_sa:
#             for i, r in enumerate(riders):
#                 data["Root"]["ProductDetails"]["Product"]["RiderDetails"]["Rider"].append({
#                     "Name": r,
#                     "SA": str(rider_sa[i]) if i < len(rider_sa) and rider_sa[i] else "0",
#                     "Term": term,
#                     "RiderOption": tracker.get_slot("rider_option") or "",
#                     "Percentage": "0",
#                     "RiderPPT": ppt
#                 })

#         # Step 4: Call the API
#         try:
#             token = get_cached_token()
            
#             # Print token, payload, and response for debugging
#             print("\n" + "="*80)
#             print("API CALL DEBUG INFO")
#             print("="*80)
#             print(f"\nTOKEN: {token}")
#             print(f"\nPAYLOAD (sent to API):")
#             print(json.dumps(data, indent=2, ensure_ascii=False))
#             print("\n" + "-"*80)
            
#             result = call_main_api(API_URL, token, data)
            
#             print(f"\nRESPONSE (received from API):")
#             print(json.dumps(result, indent=2, ensure_ascii=False))
#             print("="*80 + "\n")
            
#         except Exception as e:
#             print(f"\n❌ API CALL ERROR: {str(e)}\n")
#             dispatcher.utter_message(f"❌ Failed to get premium: {str(e)}")
#             return [SlotSet("awaiting_premium_confirmation", False)]

#         # Step 5: Handle API response - check for errors
#         if isinstance(result, dict):
#             error_code = result.get("ErrorCode", "")
#             error_msg = result.get("ErrorMessage", "")
            
#             # E00 with "Success" means success, not an error
#             is_success = (error_code == "E00" and error_msg == "Success")
            
#             # If there's an error code and it's not success, show error message
#             if error_code and not is_success:
#                 dispatcher.utter_message(
#                     text=f"Unable to generate quotation (Error {error_code}): {error_msg or 'Unknown error'}"
#                 )
#                 return [SlotSet("awaiting_premium_confirmation", False)]
            
#             # Check if premium information exists in response
#             if "PremiumSummary" not in result:
#                 error_msg = result.get("ErrorMessage", "Quotation received, but premium information is missing.")
#                 dispatcher.utter_message(f"❌ {error_msg}")
#                 return [SlotSet("awaiting_premium_confirmation", False)]

#         # Step 6: Extract and display the premium
#         try:
#             premium = result["PremiumSummary"]["TotalFirstPremium"]
#         except (KeyError, TypeError):
#             error_msg = result.get("ErrorMessage", "Quotation received, but premium key is missing.") if isinstance(result, dict) else "Quotation received, but premium key is missing."
#             dispatcher.utter_message(f"❌ {error_msg}")
#             return [SlotSet("awaiting_premium_confirmation", False)]
        
#         policy_term = data["Root"]["ProductDetails"]["Product"]["Term"]
#         ppt = data["Root"]["ProductDetails"]["Product"]["PremiumPaymentTerm"]
#         sum_assured = data["Root"]["ProductDetails"]["Product"]["DeathBenefit"]

#         # Step 7: Show the final premium result to user
#         dispatcher.utter_message(
#             text=(
#                 f"Quotation Summary: Total Premium (with tax): ₹{premium} per year\n"
#                 f"Coverage Summary\n"
#                  f"- Sum Assured: ₹{sum_assured}\n"
#                 f"- Policy Term: {policy_term} years\n"
#                 f"- Premium Payment Term (PPT): {ppt} years\n\n"
#             )
#         )

#         return [SlotSet("awaiting_premium_confirmation", False)]


"""
Insurance Quotation Bot - Custom Actions
This file contains all the custom actions that the bot performs when collecting quotation details.
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
    This action is called when the user asks for a quotation.
    If all details are already collected, it directly shows the summary.
    Otherwise, it shows instructions to collect details.
    """
    
    def name(self) -> str:
        return "action_activate_quotation_form"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[str, Any]]:
        
        # Check if all required slots are already filled
        required_slots = ["first_name", "last_name", "dob_quotation", "gender", 
                         "marital_status", "tobacco", "sum_assured", "term", "ppt"]
        
        all_filled = all(tracker.get_slot(slot) is not None and tracker.get_slot(slot) != "" 
                        for slot in required_slots)
        
        # If all slots are filled, directly show summary (skip form)
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
            # Return ActiveLoop(null) to prevent form from activating, and set confirmation flag
            return [
                ActiveLoop(None),
                SlotSet("awaiting_premium_confirmation", True)
            ]
        
        # If slots are not filled, show instructions to collect details
        message = (
            "Great! I'll help you get a quotation. Please provide me with the following details:\n"
            "• Name (First and Last name)\n"
            "• Date of Birth (e.g., 1987/04/06 or 1987 04 june)\n"
            "• Gender (Male/Female)\n"
            "• Marital Status (Married/Single)\n"
            "• Tobacco consumption (Yes/No)\n"
            "• Policy Term (e.g., 20 years)\n"
            # "• Premium Payment Term (PPT) (e.g., 10 years)\n"
            "• Sum Assured (e.g., 5000000)\n"
            "You can provide all these details in a single comma-separated message or can chat.\n"
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
        full_text = latest_message.get("text", "") or ""
        # For comma-separated inputs, normalize spaces directly after commas
        # e.g. ", 10" -> ",10" so that number extraction is consistent
        full_text = re.sub(r',\s+(\d)', r',\1', full_text)
        text = full_text.lower()
        
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
            # 1) YYYY/MM/DD or YYYY-MM-DD
            m = re.search(r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b', full_text)
            if m:
                year, month, day = m.group(1), m.group(2), m.group(3)
                extracted["dob_quotation"] = f"{year}-{int(month):02d}-{int(day):02d}"
            else:
                # 2) YYYY DD Month (e.g. 1987 04 june)
                m = re.search(
                    r'\b(\d{4})\s+(\d{1,2})\s+'
                    r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
                    full_text,
                    re.IGNORECASE,
                )
                if m:
                    year, day, month_name = m.group(1), m.group(2), m.group(3)
                    month_num = self._month_to_num(month_name)
                    extracted["dob_quotation"] = f"{year}-{month_num:02d}-{int(day):02d}"
                else:
                    # 3) YYYY Month DD (e.g. 1987 june 08)
                    m = re.search(
                        r'\b(\d{4})\s+'
                        r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+'
                        r'(\d{1,2})\b',
                        full_text,
                        re.IGNORECASE,
                    )
                    if m:
                        year, month_name, day = m.group(1), m.group(2), m.group(3)
                        month_num = self._month_to_num(month_name)
                        extracted["dob_quotation"] = f"{year}-{month_num:02d}-{int(day):02d}"
                    else:
                        # 4) DD Month YYYY (e.g. 19 june 1987)
                        m = re.search(
                            r'\b(\d{1,2})\s+'
                            r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+'
                            r'(\d{4})\b',
                            full_text,
                            re.IGNORECASE,
                        )
                        if m:
                            day, month_name, year = m.group(1), m.group(2), m.group(3)
                            month_num = self._month_to_num(month_name)
                            extracted["dob_quotation"] = f"{year}-{month_num:02d}-{int(day):02d}"
        
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
        
        # Extract policy term - First check for "term" keyword, then position-based
        if "term" not in extracted:
            # First, try to find "term" or "policy term" keyword with a number (e.g., "25 term", "25 policy term")
            # This works even if not comma-separated
            term_patterns = [
                r'\b(\d{1,2})\s*(?:years?)?\s*term\b',  # "25 term" or "25 years term"
                r'\b(\d{1,2})\s*policy\s*term\b',  # "25 policy term"
                r'term\s*(?:is|of)?\s*(\d{1,2})\s*(?:years?)?\b',  # "term is 25" or "term 25"
            ]
            for pattern in term_patterns:
                term_match = re.search(pattern, full_text, re.IGNORECASE)
                if term_match:
                    num = int(term_match.group(1))
                    if 5 <= num <= 40:
                        extracted["term"] = str(num)
                        break
            
            # If not found with keyword, try comma-separated extraction (only if 3+ parts)
            if "term" not in extracted and ',' in full_text and len(full_text.split(',')) >= 3:
                parts = full_text.split(',')
                print("\n[DEBUG] Comma-separated parts while extracting TERM:", [p.strip() for p in parts])
                for part in parts:
                    part_stripped = part.strip()
                    # Skip explicit numeric dates like 2002/09/08 or 2002-09-08
                    if re.search(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', part_stripped):
                        continue
                    # Skip natural language dates like "08 april 2002"
                    if re.search(
                        r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
                        part_stripped,
                        re.IGNORECASE,
                    ):
                        continue
                    # Skip large numbers (sum_assured)
                    if re.search(r'\d{6,}', part_stripped):
                        continue
                    # Skip if this part has "ppt" keyword (we're looking for term)
                    if re.search(r'\bppt\b', part_stripped, re.IGNORECASE):
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
        
        # Extract Premium Payment Term (PPT) - First check for "ppt" keyword, then position-based
        if "ppt" not in extracted:
            # First, try to find "ppt" keyword with a number (e.g., "5 ppt", "5 years ppt", "12 ppt")
            # This works even if not comma-separated
            ppt_patterns = [
                r'\b(\d{1,2})\s*ppt\b',  # "12 ppt" (most specific - number directly before ppt)
                r'\b(\d{1,2})\s*(?:years?)?\s*ppt\b',  # "5 ppt" or "5 years ppt"
                r'ppt\s*(?:is|of)?\s*(\d{1,2})\s*(?:years?)?\b',  # "ppt is 5" or "ppt 5"
                r'premium\s*payment\s*term.*?(\d{1,2})\s*(?:years?)?\b',  # "premium payment term 5"
            ]
            for pattern in ppt_patterns:
                ppt_match = re.search(pattern, full_text, re.IGNORECASE)
                if ppt_match:
                    num = int(ppt_match.group(1))
                    if 1 <= num <= 40:
                        extracted["ppt"] = str(num)
                        break
            
            # If not found with keyword, try comma-separated extraction (only if 3+ parts)
            if "ppt" not in extracted and ',' in full_text and len(full_text.split(',')) >= 3:
                parts = full_text.split(',')
                print("\n[DEBUG] Comma-separated parts while extracting PPT:", [p.strip() for p in parts])
                term_value = extracted.get("term")  # Get term value if already extracted
                # In comma-separated input, PPT is usually the last small number (after term)
                for part in reversed(parts):
                    part_stripped = part.strip()
                    # Skip explicit numeric dates like 2002/09/08 or 2002-09-08
                    if re.search(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', part_stripped):
                        continue
                    # Skip natural language dates like "08 april 2002"
                    if re.search(
                        r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
                        part_stripped,
                        re.IGNORECASE,
                    ):
                        continue
                    # Skip large numbers (sum_assured)
                    if re.search(r'\d{6,}', part_stripped):
                        continue
                    # Skip if this part has "term" keyword (we're looking for PPT)
                    if re.search(r'\bterm\b', part_stripped, re.IGNORECASE):
                        continue
                    numbers = re.findall(r'\b(\d{1,2})\b', part_stripped)
                    for num_str in numbers:
                        num = int(num_str)
                        if 1 <= num <= 40:
                            # If term was already extracted and this number is different, it's PPT
                            if term_value and str(num) != term_value:
                                extracted["ppt"] = str(num)
                                break
                            # If term not extracted yet, this could be PPT (last small number)
                            elif not term_value:
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
        if has_commas:
            parts_preview = [p.strip() for p in full_text.split(',')]
            print("\n[DEBUG] Comma-separated parts (extract_all_slots_from_message):", parts_preview)
        
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
                # Ignore clearly invalid numeric values like years (e.g. "2003")
                if not re.fullmatch(r"\d{2,4}", status):
                    slot_values["marital_status"] = (
                        "Married" if status in ["married", "m"]
                        else "Single" if status in ["single", "s"]
                        else status.capitalize()
                    )
            
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
                # Check for keywords first
                if "annually" in ppt_val.lower() or "yearly" in ppt_val.lower():
                    slot_values["ppt"] = "Annually"
                elif "monthly" in ppt_val.lower():
                    slot_values["ppt"] = "Monthly"
                else:
                    # Extract number from PPT value (handles "12", "12 ppt", "12 years", etc.)
                    numbers = re.findall(r'\d+', ppt_val)
                    if numbers:
                        ppt_num = int(numbers[0])
                        if 1 <= ppt_num <= 40:
                            slot_values["ppt"] = str(ppt_num)
        
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

        # 1) YYYY/MM/DD or YYYY-MM-DD
        m = re.search(r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b', full_text)
        if m:
            year, month, day = m.group(1), m.group(2), m.group(3)
            dob = f"{year}-{int(month):02d}-{int(day):02d}"
        else:
            # 2) YYYY DD Month (e.g. 1987 04 june)
            m = re.search(
                r'\b(\d{4})\s+(\d{1,2})\s+'
                r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b',
                full_text,
                re.IGNORECASE,
            )
            if m:
                year, day, month_name = m.group(1), m.group(2), m.group(3)
                month_num = self._month_to_num(month_name)
                dob = f"{year}-{month_num:02d}-{int(day):02d}"
            else:
                # 3) YYYY Month DD (e.g. 1987 june 08)
                m = re.search(
                    r'\b(\d{4})\s+'
                    r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+'
                    r'(\d{1,2})\b',
                    full_text,
                    re.IGNORECASE,
                )
                if m:
                    year, month_name, day = m.group(1), m.group(2), m.group(3)
                    month_num = self._month_to_num(month_name)
                    dob = f"{year}-{month_num:02d}-{int(day):02d}"
                else:
                    # 4) DD Month YYYY (e.g. 19 june 1987)
                    m = re.search(
                        r'\b(\d{1,2})\s+'
                        r'(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+'
                        r'(\d{4})\b',
                        full_text,
                        re.IGNORECASE,
                    )
                    if m:
                        day, month_name, year = m.group(1), m.group(2), m.group(3)
                        month_num = self._month_to_num(month_name)
                        dob = f"{year}-{month_num:02d}-{int(day):02d}"
        
        # If found in entities, use that
        if "dob_quotation" in entities and not dob:
            dob = str(entities["dob_quotation"])
        
        # If still no dob found, use the value provided
        if not dob and value:
            dob = str(value)
        
        # Clean DOB and try to parse multiple common formats, then normalise to YYYY-MM-DD
        if dob and isinstance(dob, str):
            # Use only the first part before any comma
            if ',' in dob:
                dob = dob.split(',')[0].strip()

            # Normalise whitespace
            dob_clean = re.sub(r'\s+', ' ', dob.strip())

            # Try several typical date formats:
            # - 03 june 2002 / 03 Jun 2002  -> "%d %B %Y", "%d %b %Y"
            # - 2002 june 03 / 2002 Jun 03  -> "%Y %B %d", "%Y %b %d"
            # - 2002/09/06, 2002-09-06      -> "%Y/%m/%d", "%Y-%m-%d"
            parsed_successfully = False
            for fmt in [
                "%d %B %Y",
                "%d %b %Y",
                "%Y %B %d",
                "%Y %b %d",
                "%Y/%m/%d",
                "%Y-%m-%d",
            ]:
                try:
                    parsed_date = datetime.strptime(dob_clean, fmt).date()
                    print("Converting str into date: ",parsed_date)
                    dob = parsed_date.strftime("%Y-%m-%d")
                    print("printing final formated dob: ",dob)
                    parsed_successfully = True
                    break
                except ValueError:
                    continue

            # Fallback to older regex-based handling if none of the formats matched
            if not parsed_successfully and not re.match(r'\d{4}-\d{2}-\d{2}', dob_clean):
                # Extract date pattern like 2002/09/06 or 2002-09-06
                date_match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', dob_clean)
                if date_match:
                    dob = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
                else:
                    # Try natural language dates like "1987 04 june" or "03 june 1987"
                    date_patterns = [
                        (r'(\d{4})\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
                         lambda m: f"{m.group(1)}-{self._month_to_num(m.group(3)):02d}-{int(m.group(2)):02d}"),
                        (r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})',
                         lambda m: f"{m.group(3)}-{self._month_to_num(m.group(2)):02d}-{int(m.group(1)):02d}"),
                    ]
                    for pattern, converter in date_patterns:
                        match = re.search(pattern, dob_clean, re.IGNORECASE)
                        if match:
                            dob = converter(match)
                            break
        
        # Only return if we found a valid date (YYYY-MM-DD format)
        if dob and isinstance(dob, str) and re.match(r'\d{4}-\d{2}-\d{2}', dob):
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
            status_raw = str(entities["marital_status"])
            status = status_raw.lower()
            if ',' in status:
                status = status.split(',')[0].strip()
            # If NLU accidentally tagged a year/number as marital_status (e.g. "2003"), ignore it
            if not re.fullmatch(r"\d{2,4}", status):
                if status in ["married", "m"]:
                    return {"marital_status": "Married"}
                elif status in ["single", "s"]:
                    return {"marital_status": "Single"}
                return {"marital_status": status_raw.split(',')[0].strip().capitalize()}

        # Try to infer marital status from the latest message text directly
        latest_message = tracker.latest_message
        text = (latest_message.get("text", "") or "").lower()
        if re.search(r"\bmarried\b", text):
            return {"marital_status": "Married"}
        if re.search(r"\bsingle\b", text):
            return {"marital_status": "Single"}
        if re.search(r"\bdivorced\b", text):
            return {"marital_status": "Divorced"}
        if re.search(r"\bwidowed\b", text):
            return {"marital_status": "Widowed"}

        if value:
            cleaned_value = str(value).split(',')[0].strip().capitalize()
            # Ignore pure numeric "values" (likely mis-extracted years)
            if not re.fullmatch(r"\d{2,4}", cleaned_value):
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
        # DOB validator stores value as YYYY-MM-DD (Python date / ISO format).
        # The API expects XMLSchema date (YYYY-MM-DD), so we just pass it through.
        dob_raw = tracker.get_slot("dob_quotation")
        dob = None
        if dob_raw:
            dob_str = str(dob_raw).strip()
            # If user/message added extra text after a comma, keep only the date part
            if "," in dob_str:
                dob_str = dob_str.split(",")[0].strip()
            # If it's already in YYYY-MM-DD, keep as-is; otherwise, try to parse and normalise.
            if re.match(r"\d{4}-\d{2}-\d{2}$", dob_str):
                dob = dob_str
            else:
                try:
                    # Try a few common formats, then normalise to YYYY-MM-DD
                    for fmt in ["%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"]:
                        try:
                            parsed = datetime.strptime(dob_str, fmt).date()
                            dob = parsed.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    # If none matched, fall back to original string
                    if not dob:
                        dob = dob_str
                except Exception:
                    dob = dob_str
        
        first_name = tracker.get_slot("first_name")
        last_name = tracker.get_slot("last_name")
        if first_name:
            first_name = re.sub(r'[^a-zA-Z\s-]', '', str(first_name)).strip()
        if last_name:
            last_name = re.sub(r'[^a-zA-Z\s-]', '', str(last_name)).strip()
        
        marital_status = tracker.get_slot("marital_status")
        if marital_status:
            marital_status = str(marital_status).split(',')[0].strip()
            # Clean obviously wrong numeric values like "2003" caused by mis-tagging
            if re.fullmatch(r"\d{2,4}", marital_status):
                marital_status = ""
        
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
                        # "PremiumPaymentTerm": str(tracker.get_slot("ppt")) if tracker.get_slot("ppt") else "0",
                        "PremiumPaymentTerm":"7",
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
                    text=f"Response from API:Unable to generate quotation (Error {error_code}): {error_msg or 'Unknown error'}"
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
                f"Quotation Summary: Total Premium (with tax): ₹{premium} per year\n"
                f"Coverage Summary\n"
                 f"- Sum Assured: ₹{sum_assured}\n"
                f"- Policy Term: {policy_term} years\n"
                f"- Premium Payment Term (PPT): {ppt} years\n\n"
            )
        )


        return [SlotSet("awaiting_premium_confirmation", False)]

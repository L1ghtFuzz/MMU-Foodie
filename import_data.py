import json
import os, re
from datetime import datetime, time # Needed for parsing times for OperatingHour model

# Adjust the import path if app.py is not in the same directory as this script
# Assuming your Flask app is in a file named 'app.py' in the same directory
from app import app, db, Restaurant, User, Review, OperatingHour, RestaurantImage

def import_restaurants_from_json(json_filepath):
    """
    Imports restaurant data from a raw JSON file into the database.
    Performs transformation during import and checks for existing restaurants.
    This version is specifically adapted for the detailed model structure in your app.py.
    """
    try:
        with open(json_filepath, 'r', encoding='utf-8') as f:
            raw_restaurants_data = json.load(f)
        print(f"Loaded {len(raw_restaurants_data)} raw entries from {json_filepath}")
    except FileNotFoundError:
        print(f"Error: Raw JSON file not found at '{json_filepath}'")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{json_filepath}'. Check file format.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while loading the JSON: {e}")
        return

    # All database operations need to be performed within a Flask application context.
    with app.app_context():
        imported_count = 0
        skipped_count = 0
        error_count = 0

        # Define the order of days of the week for consistent processing
        days_of_week_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for item in raw_restaurants_data:
            name = item.get('title')
            address = item.get('address')

            if not name or not address:
                print(f"Skipping entry due to missing title or address in raw data: {item.get('title', 'N/A')} - {item.get('address', 'N/A')}")
                error_count += 1
                continue

            # Check if a restaurant with the same name and address already exists
            existing_restaurant = Restaurant.query.filter_by(name=name, address=address).first()

            if existing_restaurant:
                print(f"Skipping existing restaurant: {name} at {address}")
                skipped_count += 1
                continue

            try:
                # Prepare data for Restaurant model
                new_restaurant = Restaurant(
                    name=name,
                    address=address,
                    phone=item.get('phone'),
                    cuisine=item.get('categoryName'), # Mapping categoryName to cuisine
                    price=item.get('price'), # 'price' from JSON maps to 'price' in model
                    Maps_link=item.get('website'), # Mapping 'website' from JSON to 'Maps_link' in model
                    description=item.get('description', ''), # Use description if available, else empty string
                    image_url=item.get('imageUrl'), # Use imageUrl from JSON for main image
                    latitude=item.get('location', {}).get('lat'),
                    longitude=item.get('location', {}).get('lng'),
                    is_24_hours=False # Will update based on operating hours below
                )
                db.session.add(new_restaurant)
                db.session.flush() # Use flush to get the ID for operating hours before commit

                # Process Operating Hours
                opening_hours_raw = item.get('openingHours')
                
                # First, determine if it's truly 24 hours
                is_24_hours_flag = False
                if opening_hours_raw:
                    for oh_entry in opening_hours_raw:
                        if "24 hours" in oh_entry.get('hours', '').lower() or "00:00 to 00:00" in oh_entry.get('hours', ''):
                            is_24_hours_flag = True
                            break
                new_restaurant.is_24_hours = is_24_hours_flag # Update the flag on the restaurant object

                # Store Operating Hours in the separate OperatingHour model
                if opening_hours_raw:
                    # Create a dictionary for easier lookup of hours by day
                    parsed_hours = {oh_entry['day']: oh_entry['hours'] for oh_entry in opening_hours_raw}

                    for day in days_of_week_ordered:
                        hours_str = parsed_hours.get(day)
                        
                        open_time_str = None
                        close_time_str = None

                        if is_24_hours_flag:
                            open_time_str = '00:00'
                            close_time_str = '00:00'
                        elif hours_str and hours_str.lower() != 'closed':
                            # Attempt to parse specific times like "10 AM to 10 PM"
                            # This needs to be robust to various formats.
                            # A simple approach for "X AM to Y PM" like formats:
                            try:
                                # Example: "10:00 AM to 9:00 PM" -> Needs more robust parsing if format varies
                                if 'to' in hours_str:
                                    parts = hours_str.split('to')
                                    # This is a basic conversion, may need more sophisticated regex for "9\u202fPM"
                                    # Assuming standard HH:MM format after clean up
                                    # Simple heuristic for common Google Maps formats (e.g. 10 AM, 10 PM)
                                    open_part = parts[0].strip().replace('\u202f', ' ')
                                    close_part = parts[1].strip().replace('\u202f', ' ')

                                    # Attempt to convert to 24-hour format
                                    try:
                                        open_time_obj = datetime.strptime(open_part, '%I:%M %p').time()
                                        open_time_str = open_time_obj.strftime('%H:%M')
                                    except ValueError:
                                        try: # Try without minutes (e.g., "10 AM")
                                            open_time_obj = datetime.strptime(open_part, '%I %p').time()
                                            open_time_str = open_time_obj.strftime('%H:%M')
                                        except ValueError:
                                            # Fallback if specific format not found, or log for inspection
                                            pass

                                    try:
                                        close_time_obj = datetime.strptime(close_part, '%I:%M %p').time()
                                        close_time_str = close_time_obj.strftime('%H:%M')
                                    except ValueError:
                                        try: # Try without minutes (e.g., "10 PM")
                                            close_time_obj = datetime.strptime(close_part, '%I %p').time()
                                            close_time_str = close_time_obj.strftime('%H:%M')
                                        except ValueError:
                                            # Fallback if specific format not found
                                            pass
                                # If the hours_str is already in HH:MM format, use directly
                                elif re.match(r'^\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}$', hours_str):
                                    open_time_str = hours_str.split('-')[0].strip()
                                    close_time_str = hours_str.split('-')[1].strip()
                            except Exception as parse_e:
                                print(f"Warning: Could not parse hours '{hours_str}' for {day} of {name}: {parse_e}")
                                # Keep times as None if parsing fails
                                open_time_str = None
                                close_time_str = None
                        elif hours_str and hours_str.lower() == 'closed':
                            open_time_str = 'Closed'
                            close_time_str = None # No close time for closed days

                        if open_time_str: # Only add if we have some valid open time
                            new_operating_hour = OperatingHour(
                                restaurant=new_restaurant, # Link to the newly created restaurant
                                day_of_week=day,
                                open_time=open_time_str,
                                close_time=close_time_str
                            )
                            db.session.add(new_operating_hour)
                else:
                    # If no openingHours data provided in JSON, mark all as closed by default
                    for day in days_of_week_ordered:
                        new_operating_hour = OperatingHour(
                            restaurant=new_restaurant,
                            day_of_week=day,
                            open_time='Closed',
                            close_time=None
                        )
                        db.session.add(new_operating_hour)

                # No need to commit images as a separate loop if image_url is on main restaurant model
                # If you want to add to RestaurantImage model too, you'd add:
                # if item.get('imageUrl'):
                #     db.session.add(RestaurantImage(image_url=item['imageUrl'], restaurant=new_restaurant))


                db.session.commit() # Commit new restaurant and its operating hours
                imported_count += 1
                print(f"Successfully imported: {name}")

            except Exception as e:
                db.session.rollback() # Rollback changes if an error occurs during this entry
                print(f"Error importing restaurant '{name}' at '{address}': {e}")
                print(f"Full error details for {name}: {e}")
                error_count += 1
        
        print("\n--- Import Summary ---")
        print(f"Total raw entries processed: {len(raw_restaurants_data)}")
        print(f"Successfully imported: {imported_count}")
        print(f"Skipped (already exists): {skipped_count}")
        print(f"Errors during import: {error_count}")

if __name__ == '__main__':
    # Define the path to your raw JSON file
    # Make sure 'dataset_google-maps-extractor-task_2025-06-13_09-10-35-666.json' is in the same directory
    json_file = 'dataset_google-maps-extractor-task_2025-06-13_09-10-35-666.json'

    # Run the import function
    import_restaurants_from_json(json_file)

# THIS IS THE TIME CALCULATION FIX FOR NOTESHEET_DETAIL ROUTE
# Replace lines 359-394 in your app.py with this:

    # Calculate days held at each stage
    # Order: movements[0] = newest (current), movements[-1] = oldest (first receipt)
    from datetime import datetime as dt
    for i, movement in enumerate(movements):
        # Use date-only for display
        movement['display_date'] = movement['forward_date_only']
        
        # Calculate IN and OUT times for this location
        in_date_str = movement['forward_date_only']  # When document arrived at this location
        
        if i == 0:
            # Current location - still here (no OUT date yet)
            try:
                in_date = dt.strptime(in_date_str, '%Y-%m-%d').date()
                today = dt.now().date()
                days_diff = (today - in_date).days
                
                if days_diff == 0:
                    movement['time_held'] = "Today (current)"
                    movement['status_badge'] = "🟢 Current Location"
                elif days_diff == 1:
                    movement['time_held'] = "1 day (current)"
                    movement['status_badge'] = "🟢 Current Location"
                else:
                    movement['time_held'] = f"{days_diff} days (current)"
                    movement['status_badge'] = "🟢 Current Location"
            except Exception as e:
                movement['time_held'] = "Unknown (current)"
                movement['status_badge'] = "🟢 Current Location"
        else:
            # Past location - calculate how long document stayed here
            # OUT date = date of NEXT movement (movements[i-1] because newest first)
            try:
                in_date = dt.strptime(in_date_str, '%Y-%m-%d').date()
                out_date = dt.strptime(movements[i-1]['forward_date_only'], '%Y-%m-%d').date()
                days_diff = (out_date - in_date).days
                
                if days_diff == 0:
                    movement['time_held'] = "Same day"
                elif days_diff == 1:
                    movement['time_held'] = "1 day"
                else:
                    movement['time_held'] = f"{days_diff} days"
                
                # Show IN and OUT dates
                movement['in_date'] = in_date_str
                movement['out_date'] = movements[i-1]['forward_date_only']
            except Exception as e:
                movement['time_held'] = "Unknown"
    
    # Get sections for forwarding dropdown
    sections = db.get_all_sections()


# EXPLANATION:
# movements[0] = 2026-01-10 Received (current) → Time = today - Jan 10 = 0 days
# movements[1] = 2026-01-08 Forward to DCC → Time = Jan 10 - Jan 8 = 2 days (stayed at DCC 2 days)
# movements[2] = 2026-01-03 Forward to Admin → Time = Jan 8 - Jan 3 = 5 days (stayed at Admin 5 days)

# THIS SHOWS: How long document stayed at EACH location before moving to next location
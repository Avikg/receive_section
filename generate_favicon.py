"""
Generate favicon.ico for WBSEDCL Tracking System
Requires: pip install pillow
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    
    # Create a 32x32 image with blue background
    img = Image.new('RGB', (32, 32), color='#0d6efd')
    draw = ImageDraw.Draw(img)
    
    # Draw white building
    # Building body
    draw.rectangle([8, 6, 23, 25], fill='white')
    
    # Windows (blue squares)
    window_color = '#0d6efd'
    
    # Row 1
    draw.rectangle([10, 8, 12, 10], fill=window_color)
    draw.rectangle([15, 8, 17, 10], fill=window_color)
    draw.rectangle([20, 8, 22, 10], fill=window_color)
    
    # Row 2
    draw.rectangle([10, 13, 12, 15], fill=window_color)
    draw.rectangle([15, 13, 17, 15], fill=window_color)
    draw.rectangle([20, 13, 22, 15], fill=window_color)
    
    # Row 3
    draw.rectangle([10, 18, 12, 20], fill=window_color)
    draw.rectangle([15, 18, 17, 20], fill=window_color)
    draw.rectangle([20, 18, 22, 20], fill=window_color)
    
    # Door
    draw.rectangle([14, 22, 17, 25], fill=window_color)
    
    # Save as ICO (supports multiple sizes)
    img.save('favicon.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
    
    print("✅ favicon.ico created successfully!")
    print("📁 Place it in the 'static' folder")
    print("🔵 Icon: Blue building with white windows")
    
except ImportError:
    print("❌ Pillow library not installed")
    print("Run: pip install pillow")
    print("")
    print("Alternative: Use the create_favicon.html file")
    print("1. Open create_favicon.html in browser")
    print("2. Click 'Generate & Download Favicon'")
    print("3. Move favicon.ico to static folder")
except Exception as e:
    print(f"❌ Error: {e}")
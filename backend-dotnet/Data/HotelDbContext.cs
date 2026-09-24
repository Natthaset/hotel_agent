using backend_dotnet.Models;
using Microsoft.EntityFrameworkCore;

namespace backend_dotnet.Data;

public class HotelDbContext(DbContextOptions<HotelDbContext> options) : DbContext(options)
{
    public DbSet<Room> Rooms => Set<Room>();
    public DbSet<Booking> Bookings => Set<Booking>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        // Room entity configuration
        modelBuilder.Entity<Room>(entity =>
        {
            entity.HasKey(r => r.Id);
            entity.Property(r => r.Name).IsRequired().HasMaxLength(150);
            entity.Property(r => r.Type).IsRequired().HasMaxLength(100);
            entity.Property(r => r.PricePerNight).HasPrecision(18, 2);
            entity.Property(r => r.Description).HasMaxLength(1000);
            entity.Property(r => r.Amenities).HasMaxLength(500);

            // Seed Data for 5-star hotel rooms
            entity.HasData(
                new Room
                {
                    Id = 1,
                    Name = "Deluxe Ocean King",
                    Type = "Deluxe King",
                    PricePerNight = 6500.00m,
                    Capacity = 2,
                    Description = "Spacious ocean-view room with king-size signature bed, private balcony, and marble bath.",
                    Amenities = "King Bed, Ocean View, Private Balcony, Free Breakfast, High-Speed WiFi, Espresso Machine",
                    IsActive = true
                },
                new Room
                {
                    Id = 2,
                    Name = "Executive Panorama Suite",
                    Type = "Executive Suite",
                    PricePerNight = 11200.00m,
                    Capacity = 2,
                    Description = "High-floor luxury corner suite offering 180-degree sunset ocean panorama with Executive Lounge access.",
                    Amenities = "King Bed, 180° Panoramic View, Club Lounge Access, Airport Limousine, Deep Soak Tub",
                    IsActive = true
                },
                new Room
                {
                    Id = 3,
                    Name = "Lagoon View Twin Villa",
                    Type = "Twin Villa",
                    PricePerNight = 7800.00m,
                    Capacity = 2,
                    Description = "Private tropical garden villa featuring two double beds and direct access to lagoon swimming pool.",
                    Amenities = "2 Queen Beds, Direct Pool Access, Garden Patio, Daily Afternoon Tea, Rainforest Shower",
                    IsActive = true
                },
                new Room
                {
                    Id = 4,
                    Name = "Grand Azure Family Residence",
                    Type = "Family Suite",
                    PricePerNight = 14500.00m,
                    Capacity = 4,
                    Description = "Two-bedroom grand suite with separate dining area, kitchenette, and dedicated children play amenities.",
                    Amenities = "1 King + 2 Twin Beds, Kitchenette, Living & Dining Room, Complimentary Laundry, Kids Club Pass",
                    IsActive = true
                },
                new Room
                {
                    Id = 5,
                    Name = "Royal Beachfront Penthouse",
                    Type = "Penthouse",
                    PricePerNight = 28000.00m,
                    Capacity = 6,
                    Description = "Top-floor ultra-luxury presidential penthouse with private rooftop infinity pool, personal butler, and private chef dining.",
                    Amenities = "3 En-suite Bedrooms, Private Infinity Pool, 24/7 Dedicated Butler, Private Wine Cellar, Helicopter Pad Access",
                    IsActive = true
                }
            );
        });

        // Booking entity configuration
        modelBuilder.Entity<Booking>(entity =>
        {
            entity.HasKey(b => b.Id);
            entity.Property(b => b.CustomerName).IsRequired().HasMaxLength(150);
            entity.Property(b => b.TotalPrice).HasPrecision(18, 2);
            entity.Property(b => b.Status).IsRequired().HasMaxLength(50);

            entity.HasOne(b => b.Room)
                  .WithMany(r => r.Bookings)
                  .HasForeignKey(b => b.RoomId)
                  .OnDelete(DeleteBehavior.Restrict);
        });
    }
}

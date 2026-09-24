namespace backend_dotnet.Models;

public class Room
{
    public int Id { get; set; }
    public required string Name { get; set; }
    public required string Type { get; set; } // e.g. "Deluxe King", "Executive Suite", "Twin Villa"
    public decimal PricePerNight { get; set; }
    public int Capacity { get; set; } = 2;
    public string Description { get; set; } = string.Empty;
    public string Amenities { get; set; } = string.Empty; // Comma-separated or JSON
    public bool IsActive { get; set; } = true;

    // Navigation property
    public ICollection<Booking> Bookings { get; set; } = new List<Booking>();
}

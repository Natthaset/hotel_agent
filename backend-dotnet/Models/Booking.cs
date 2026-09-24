namespace backend_dotnet.Models;

public class Booking
{
    public int Id { get; set; }
    public required string CustomerName { get; set; }
    public DateTime CheckInDate { get; set; }
    public DateTime CheckOutDate { get; set; }
    public int RoomId { get; set; }
    public int Pax { get; set; } = 1;
    public decimal TotalPrice { get; set; }
    public string Status { get; set; } = "Confirmed"; // "Confirmed", "Cancelled", "Pending"
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    // Navigation property
    public Room? Room { get; set; }
}

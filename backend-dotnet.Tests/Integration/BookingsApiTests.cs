using System.Net;
using System.Net.Http.Json;
using backend_dotnet.DTOs;
using FluentAssertions;
using Xunit;

namespace backend_dotnet.Tests.Integration;

public class BookingsApiTests : IClassFixture<CustomWebApplicationFactory>
{
    private readonly HttpClient _client;

    public BookingsApiTests(CustomWebApplicationFactory factory)
    {
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task CreateBooking_WithValidData_ShouldPersistAndReturn201Created()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.AddDays(14).Date;
        var checkOut = DateTime.UtcNow.AddDays(17).Date; // 3 nights
        var payload = new BookingRequestDto(
            CustomerName: "Dr. Thanawat",
            CheckInDate: checkIn,
            CheckOutDate: checkOut,
            RoomId: 1, // Deluxe Ocean King (6,500 THB/night)
            Pax: 2
        );

        // Act
        var response = await _client.PostAsJsonAsync("/api/v1/bookings", payload);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.Created);
        response.Headers.Location.Should().NotBeNull();

        var created = await response.Content.ReadFromJsonAsync<BookingResponseDto>();
        created.Should().NotBeNull();
        created!.Id.Should().BeGreaterThan(0);
        created.CustomerName.Should().Be("Dr. Thanawat");
        created.TotalNights.Should().Be(3);
        created.TotalPrice.Should().Be(19500.00m); // 3 * 6,500
        created.Status.Should().Be("Confirmed");

        // Follow up GET to verify persistence
        var getResponse = await _client.GetAsync($"/api/v1/bookings/{created.Id}");
        getResponse.StatusCode.Should().Be(HttpStatusCode.OK);
        var fetched = await getResponse.Content.ReadFromJsonAsync<BookingResponseDto>();
        fetched.Should().NotBeNull();
        fetched!.CustomerName.Should().Be("Dr. Thanawat");
    }

    [Fact]
    public async Task CreateBooking_WithMissingCustomerName_ShouldReturn400BadRequest()
    {
        // Arrange: Missing required CustomerName
        var invalidPayload = new
        {
            CustomerName = "",
            CheckInDate = DateTime.UtcNow.AddDays(10),
            CheckOutDate = DateTime.UtcNow.AddDays(12),
            RoomId = 1,
            Pax = 2
        };

        // Act
        var response = await _client.PostAsJsonAsync("/api/v1/bookings", invalidPayload);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.BadRequest);
    }

    [Fact]
    public async Task CreateBooking_WhenPartySizeExceedsRoomCapacity_ShouldReturn400BadRequest()
    {
        // Arrange: Room 1 capacity is 2, request 5 guests
        var payload = new BookingRequestDto(
            CustomerName: "Big Family",
            CheckInDate: DateTime.UtcNow.AddDays(20),
            CheckOutDate: DateTime.UtcNow.AddDays(22),
            RoomId: 1,
            Pax: 5
        );

        // Act
        var response = await _client.PostAsJsonAsync("/api/v1/bookings", payload);

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.BadRequest);
        var content = await response.Content.ReadAsStringAsync();
        content.Should().Contain("capacity");
    }

    [Fact]
    public async Task GetBookingById_WhenNotFound_ShouldReturn404NotFound()
    {
        // Act
        var response = await _client.GetAsync("/api/v1/bookings/99999");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.NotFound);
    }
}

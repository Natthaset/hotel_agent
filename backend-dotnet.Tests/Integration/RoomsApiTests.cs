using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using backend_dotnet.DTOs;
using FluentAssertions;
using Xunit;

namespace backend_dotnet.Tests.Integration;

public class RoomsApiTests : IClassFixture<CustomWebApplicationFactory>
{
    private readonly HttpClient _client;

    public RoomsApiTests(CustomWebApplicationFactory factory)
    {
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task HealthEndpoint_ShouldReturnHealthy()
    {
        // Act
        var response = await _client.GetAsync("/health");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var content = await response.Content.ReadAsStringAsync();
        content.Should().Contain("Healthy");
        content.Should().Contain("Hotel.Backend.DotNet10");
    }

    [Fact]
    public async Task GetAvailability_WithoutDates_ShouldReturnAllActiveRooms()
    {
        // Act
        var response = await _client.GetAsync("/api/v1/rooms/availability");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var rooms = await response.Content.ReadFromJsonAsync<List<RoomDto>>();
        rooms.Should().NotBeNull();
        rooms!.Count.Should().BeGreaterThanOrEqualTo(5);
        rooms.Should().Contain(r => r.Name == "Deluxe Ocean King");
    }

    [Fact]
    public async Task GetAvailability_WithFutureDates_ShouldReturnAvailableRooms()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.AddDays(7).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        var checkOut = DateTime.UtcNow.AddDays(10).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

        // Act
        var response = await _client.GetAsync($"/api/v1/rooms/availability?checkIn={checkIn}&checkOut={checkOut}&roomType=Penthouse");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var rooms = await response.Content.ReadFromJsonAsync<List<RoomDto>>();
        rooms.Should().NotBeNull();
        rooms!.Should().ContainSingle(r => r.Type == "Penthouse");
    }

    [Fact]
    public async Task GetAvailability_WithPastCheckInDate_ShouldReturn400BadRequest()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.AddDays(-2).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        var checkOut = DateTime.UtcNow.AddDays(2).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

        // Act
        var response = await _client.GetAsync($"/api/v1/rooms/availability?checkIn={checkIn}&checkOut={checkOut}");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.BadRequest);
    }

    [Fact]
    public async Task GetById_WhenRoomExists_ShouldReturnRoomDetails()
    {
        // Act
        var response = await _client.GetAsync("/api/v1/rooms/1");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.OK);
        var room = await response.Content.ReadFromJsonAsync<RoomDto>();
        room.Should().NotBeNull();
        room!.Id.Should().Be(1);
        room.Name.Should().Be("Deluxe Ocean King");
    }

    [Fact]
    public async Task GetById_WhenRoomDoesNotExist_ShouldReturn404NotFound()
    {
        // Act
        var response = await _client.GetAsync("/api/v1/rooms/99999");

        // Assert
        response.StatusCode.Should().Be(HttpStatusCode.NotFound);
    }
}

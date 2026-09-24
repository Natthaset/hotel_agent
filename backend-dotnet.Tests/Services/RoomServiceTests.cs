using backend_dotnet.Models;
using backend_dotnet.Repositories;
using backend_dotnet.Services;
using FluentAssertions;
using Microsoft.Extensions.Logging;
using NSubstitute;
using NSubstitute.ExceptionExtensions;
using Xunit;

namespace backend_dotnet.Tests.Services;

public class RoomServiceTests
{
    private readonly IRoomRepository _roomRepo = Substitute.For<IRoomRepository>();
    private readonly ILogger<RoomService> _logger = Substitute.For<ILogger<RoomService>>();
    private readonly RoomService _sut;

    public RoomServiceTests()
    {
        _sut = new RoomService(_roomRepo, _logger);
    }

    [Fact]
    public async Task GetAvailableRoomsAsync_ShouldFail_WhenCheckInDateIsInPast()
    {
        // Arrange
        var pastCheckIn = DateTime.UtcNow.AddDays(-1);
        var checkOut = DateTime.UtcNow.AddDays(2);

        // Act
        var result = await _sut.GetAvailableRoomsAsync(pastCheckIn, checkOut, null);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(400);
        result.Error.Should().Contain("past");
    }

    [Fact]
    public async Task GetAvailableRoomsAsync_ShouldFail_WhenCheckOutDateIsBeforeOrEqualToCheckIn()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.AddDays(2);
        var checkOut = DateTime.UtcNow.AddDays(1);

        // Act
        var result = await _sut.GetAvailableRoomsAsync(checkIn, checkOut, null);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(400);
        result.Error.Should().Contain("Check-out date must be after check-in date");
    }

    [Fact]
    public async Task GetAvailableRoomsAsync_ShouldReturnRooms_WhenDatesAreValid()
    {
        // Arrange
        var checkIn = DateTime.UtcNow.AddDays(3);
        var checkOut = DateTime.UtcNow.AddDays(5);
        var rooms = new List<Room>
        {
            new() { Id = 1, Name = "Deluxe Ocean Suite", Type = "Suite", PricePerNight = 6500m, Capacity = 2, IsActive = true },
            new() { Id = 2, Name = "Royal Pool Villa", Type = "Villa", PricePerNight = 15000m, Capacity = 4, IsActive = true }
        };

        _roomRepo.GetAvailableRoomsAsync(checkIn, checkOut, "Villa", Arg.Any<CancellationToken>())
            .Returns([rooms[1]]);

        // Act
        var result = await _sut.GetAvailableRoomsAsync(checkIn, checkOut, "Villa");

        // Assert
        result.IsSuccess.Should().BeTrue();
        result.Value.Should().NotBeNull();
        result.Value!.Should().HaveCount(1);
        result.Value[0].Name.Should().Be("Royal Pool Villa");
    }

    [Fact]
    public async Task GetAvailableRoomsAsync_ShouldHandleInternalErrorGracefully()
    {
        // Arrange
        _roomRepo.GetAvailableRoomsAsync(Arg.Any<DateTime?>(), Arg.Any<DateTime?>(), Arg.Any<string?>(), Arg.Any<CancellationToken>())
            .Throws(new InvalidOperationException("DB connection timeout"));

        // Act
        var result = await _sut.GetAvailableRoomsAsync(null, null, null);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(500);
        result.Error.Should().Contain("internal server error");
    }

    [Fact]
    public async Task GetByIdAsync_ShouldReturnNotFound_WhenRoomDoesNotExist()
    {
        // Arrange
        _roomRepo.GetByIdAsync(999, Arg.Any<CancellationToken>()).Returns((Room?)null);

        // Act
        var result = await _sut.GetByIdAsync(999);

        // Assert
        result.IsSuccess.Should().BeFalse();
        result.StatusCode.Should().Be(404);
        result.Error.Should().Contain("not found");
    }

    [Fact]
    public async Task GetByIdAsync_ShouldReturnRoomDto_WhenRoomExists()
    {
        // Arrange
        var room = new Room
        {
            Id = 5,
            Name = "Penthouse Suite",
            Type = "Suite",
            PricePerNight = 25000m,
            Capacity = 6,
            Description = "Panoramic sea view",
            Amenities = "Private pool, Butler service",
            IsActive = true
        };

        _roomRepo.GetByIdAsync(5, Arg.Any<CancellationToken>()).Returns(room);

        // Act
        var result = await _sut.GetByIdAsync(5);

        // Assert
        result.IsSuccess.Should().BeTrue();
        result.Value.Should().NotBeNull();
        result.Value!.Id.Should().Be(5);
        result.Value.Name.Should().Be("Penthouse Suite");
        result.Value.PricePerNight.Should().Be(25000m);
    }
}

using backend_dotnet.Data;
using Microsoft.EntityFrameworkCore;

namespace backend_dotnet.Data;

public static class DbInitializer
{
    public static async Task InitializeDatabaseAsync(IServiceProvider serviceProvider, ILogger logger)
    {
        using var scope = serviceProvider.CreateScope();
        var context = scope.ServiceProvider.GetRequiredService<HotelDbContext>();

        var maxRetries = 10;
        var delay = TimeSpan.FromSeconds(3);

        for (int attempt = 1; attempt <= maxRetries; attempt++)
        {
            try
            {
                logger.LogInformation("Attempting to connect and ensure database is created (Attempt {Attempt}/{MaxRetries})...", attempt, maxRetries);
                await context.Database.EnsureCreatedAsync();
                logger.LogInformation("Database initialized and seed data successfully applied.");
                return;
            }
            catch (Exception ex)
            {
                logger.LogWarning(ex, "Database connection attempt {Attempt} failed. Retrying in {Delay}s...", attempt, delay.TotalSeconds);
                if (attempt == maxRetries)
                {
                    logger.LogError(ex, "Could not initialize database after {MaxRetries} attempts.", maxRetries);
                    throw;
                }
                await Task.Delay(delay);
            }
        }
    }
}

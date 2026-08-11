using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Reflection;

namespace AuthenticControls.Plugin
{
    internal static class AuthenticControlsMenuIcon
    {
        private const string ResourceName =
            "AuthenticControls.Plugin.Assets.authentic-controls-mark.png";

        internal static Bitmap Create()
        {
            return Create(24);
        }

        internal static Bitmap CreateHeader()
        {
            return Create(64);
        }

        private static Bitmap Create(int size)
        {
            Assembly assembly = typeof(AuthenticControlsMenuIcon).Assembly;
            using (Stream stream = assembly.GetManifestResourceStream(ResourceName))
            {
                if (stream == null)
                {
                    throw new InvalidOperationException(
                        "Authentic Controls icon resource is missing.");
                }
                using (var source = new Bitmap(stream))
                {
                    var bitmap = new Bitmap(
                        size,
                        size,
                        PixelFormat.Format32bppArgb);
                    using (Graphics graphics = Graphics.FromImage(bitmap))
                    {
                        graphics.Clear(Color.Transparent);
                        graphics.SmoothingMode = SmoothingMode.HighQuality;
                        graphics.InterpolationMode =
                            InterpolationMode.HighQualityBicubic;
                        graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
                        graphics.CompositingQuality =
                            CompositingQuality.HighQuality;
                        graphics.DrawImage(
                            source,
                            new Rectangle(0, 0, size, size),
                            new Rectangle(0, 0, source.Width, source.Height),
                            GraphicsUnit.Pixel);
                    }
                    return bitmap;
                }
            }
        }
    }
}

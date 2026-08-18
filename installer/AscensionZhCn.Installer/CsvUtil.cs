using System.Text;

namespace AscensionZhCn.Installer;

internal static class CsvUtil
{
    public static List<string[]> ReadRows(string path)
    {
        var text = File.ReadAllText(path);
        var rows = new List<string[]>();
        var fields = new List<string>();
        var field = new StringBuilder();
        var inQuotes = false;
        for (var i = 0; i < text.Length; i++)
        {
            var ch = text[i];
            if (inQuotes)
            {
                if (ch == '"')
                {
                    if (i + 1 < text.Length && text[i + 1] == '"')
                    {
                        field.Append('"');
                        i++;
                    }
                    else
                        inQuotes = false;
                }
                else
                    field.Append(ch);
                continue;
            }

            if (ch == '"')
            {
                inQuotes = true;
                continue;
            }
            if (ch == ',')
            {
                fields.Add(field.ToString());
                field.Clear();
                continue;
            }
            if (ch == '\r')
                continue;
            if (ch == '\n')
            {
                fields.Add(field.ToString());
                field.Clear();
                if (fields.Count > 1 || fields[0].Length > 0)
                    rows.Add(fields.ToArray());
                fields.Clear();
                continue;
            }
            field.Append(ch);
        }
        if (field.Length > 0 || fields.Count > 0)
        {
            fields.Add(field.ToString());
            if (fields.Count > 1 || fields[0].Length > 0)
                rows.Add(fields.ToArray());
        }
        return rows;
    }

    public static Dictionary<string, string> TwoCol(string path, string keyHeader, string valueHeader)
    {
        var rows = ReadRows(path);
        var map = new Dictionary<string, string>(StringComparer.Ordinal);
        if (rows.Count == 0)
            return map;
        var header = rows[0];
        var ki = Array.IndexOf(header, keyHeader);
        var vi = Array.IndexOf(header, valueHeader);
        var start = 0;
        if (ki >= 0 && vi >= 0)
            start = 1;
        else
        {
            ki = 0;
            vi = Math.Min(1, header.Length - 1);
        }
        for (var r = start; r < rows.Count; r++)
        {
            var row = rows[r];
            if (row.Length <= Math.Max(ki, vi))
                continue;
            var key = row[ki].Trim();
            var val = row[vi];
            if (key.Length == 0 || key is "key" or "en" || val.Length == 0)
                continue;
            map[key] = val;
        }
        return map;
    }

    public static Dictionary<string, Dictionary<string, string>> Named(string path)
    {
        var rows = ReadRows(path);
        var result = new Dictionary<string, Dictionary<string, string>>(StringComparer.Ordinal);
        if (rows.Count < 2)
            return result;
        var header = rows[0];
        var idIndex = Array.IndexOf(header, "id");
        if (idIndex < 0)
            idIndex = 0;
        for (var r = 1; r < rows.Count; r++)
        {
            var row = rows[r];
            if (row.Length <= idIndex || string.IsNullOrEmpty(row[idIndex]))
                continue;
            var record = new Dictionary<string, string>(StringComparer.Ordinal);
            for (var c = 0; c < header.Length && c < row.Length; c++)
                record[header[c]] = row[c];
            result[row[idIndex]] = record;
        }
        return result;
    }
}

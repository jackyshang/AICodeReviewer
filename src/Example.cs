using System;
using System.Collections.Generic;

namespace Example
{
    public class DataProcessor
    {
        private readonly List<string> _data = new();
        
        // BUG: No null check
        public void ProcessData(string input)
        {
            _data.Add(input.Trim());  // Will crash if input is null
        }
        
        // SECURITY: SQL injection risk
        public string BuildQuery(string userInput)
        {
            return $"SELECT * FROM Users WHERE Name = '{userInput}'";
        }
        
        // PERFORMANCE: Inefficient string concatenation in loop
        public string ConcatenateData()
        {
            string result = "";
            foreach (var item in _data)
            {
                result += item + ", ";  // Should use StringBuilder
            }
            return result;
        }
    }
}
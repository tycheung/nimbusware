package com.example;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class CalculatorTest {
    @Test
    public void addSumsOperands() {
        assertEquals(5, Calculator.add(2, 3));
    }
}

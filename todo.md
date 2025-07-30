# Add Maximum Position Weight Cap to Portfolio Builder

## Goal
Implement a 10% maximum position weight constraint to ensure no single position can exceed 10% of the portfolio, preventing concentration risk.

## Analysis
Current system sizes positions based on risk and conviction but has no upper limit. We need to:
- Add a cap after risk-based sizing but before volatility scaling
- Redistribute excess weight proportionally to other positions
- Maintain long/short balance and target exposures

## Plan

### 1. Add Max Weight Parameter
- [ ] Add `max_position_weight` parameter to class constructor (default 0.10)
- [ ] Update docstring to document the new parameter

### 2. Create Weight Capping Method
- [ ] Create `_apply_position_weight_cap()` method
- [ ] Cap any weights exceeding the maximum
- [ ] Redistribute excess weight proportionally to uncapped positions
- [ ] Preserve long/short separation during redistribution

### 3. Integrate Weight Capping into Portfolio Building
- [ ] Apply cap after risk-based weighting in `risk_based_portfolio()`
- [ ] Apply before volatility scaling to ensure cap is meaningful
- [ ] Ensure net exposure targets are still met after capping

### 4. Update Display and Reporting
- [ ] Show when positions hit the cap in portfolio allocation table
- [ ] Add summary of capped positions if any

## Implementation Details

### Weight Capping Logic:
1. Identify positions exceeding max weight
2. Cap them at max weight
3. Calculate excess weight to redistribute
4. Redistribute proportionally among uncapped positions in same group (long/short)
5. Iterate until no positions exceed cap

### Edge Cases to Handle:
- All positions in a group hitting the cap
- Very high conviction positions being capped
- Maintaining target net exposure after capping

## Files to Modify
- `backend/src/calculations/risk_calculations/correlation_portfolio_builder.py`

## Review

### Summary of Changes Made

✅ **Successfully implemented 10% position weight cap functionality**

### Changes Made:

1. **Added max_position_weight parameter**:
   - Added to constructor with default value of 0.10 (10%)
   - Updated docstring to document the parameter

2. **Created weight capping methods**:
   - `_apply_position_weight_cap()`: Main method that applies cap to both long and short positions separately
   - `_cap_weights_group()`: Helper method that caps weights within a group and redistributes excess proportionally
   - Uses iterative approach to handle cases where redistribution causes other positions to exceed cap

3. **Integrated into portfolio building flow**:
   - Applied after risk-based weighting and target net exposure calculations
   - Applied before position signs and volatility scaling
   - Preserves long/short balance and target exposures

4. **Updated display output**:
   - Added "Note" column to portfolio allocation table showing "CAPPED" for positions at the limit
   - Added summary section showing number and list of capped positions
   - Uses small tolerance (0.0001) for float comparison when checking if position hit cap

### Key Features:
- **10% maximum weight**: No single position can exceed 10% of the portfolio
- **Proportional redistribution**: Excess weight redistributed to uncapped positions in same group
- **Long/short separation**: Maintains balance by handling long and short positions separately
- **Clear visibility**: Shows which positions hit the cap in the output

The implementation is simple and effective, preventing concentration risk while maintaining the portfolio's risk-based allocation strategy.

### Fix Applied:
- Moved cap application to AFTER volatility scaling to ensure positions are actually limited to 10%
- Created `_apply_position_weight_cap_signed()` method to handle signed weights (positive/negative)
- Now the cap is applied on the final scaled weights, ensuring no position exceeds 10% in the final portfolio
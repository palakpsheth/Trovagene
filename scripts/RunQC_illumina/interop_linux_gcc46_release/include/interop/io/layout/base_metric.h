/** Basic layouts describing metric identifiers
 *
 * The layout of a binary InterOp generally has the following parts:
 *      1. Header
 *      2. Record(s)
 *
 * The classes contained in this file define two types of metric identifiers: Per Tile and Per Tile Per Cycle.
 *
 * @note These classes are packed such that there is not padding. Their size reflects the accumulation of their member fields.
 *
 *  @file
 *  @date 7/30/15
 *  @version 1.0
 *  @copyright GNU Public License.
 */

#pragma once

#include <cstddef>
#include "interop/util/static_assert.h"
#include "interop/util/cstdint.h"

namespace illumina { namespace interop { namespace io { namespace layout
{
#pragma pack(1)

    /** Base class for InterOp records that contain tile specific metrics
     *
     * These records contain both a lane and tile identifier.
     *
     * @note These classes are packed such that there is not padding. Their size reflects the accumulation of their
     * member fields.
     */
    struct base_metric
    {
        /** Define a record size type */
        typedef ::uint8_t record_size_t;

        /** Constructor
         *
         * @param lane_ lane number
         * @param tile_ tile number
         */
        base_metric(::uint16_t lane_ = 0, ::uint16_t tile_ = 0) :
                lane(lane_), tile(tile_)
        {
            static_assert(sizeof(::uint16_t) == 2, "16-bit int not supported");
            static_assert(sizeof(::uint32_t) == 4, "32-bit int not supported");
        }

        /** Set the lane and tile id from a base metric
         *
         * @param metric a base_metric from the model
         */
        template<class BaseMetric>
        void set(const BaseMetric &metric)
        {
            lane = static_cast< ::uint16_t >(metric.lane());
            tile = static_cast< ::uint16_t >(metric.tile());
        }

        /** Test if the layout contains valid data
         *
         * @return true if data is valid
         */
        bool is_valid(const bool check_tile) const
        {
            return (!check_tile || tile > 0) && lane > 0;
        }

        /** Lane number
         */
        ::uint16_t lane;
        /** Tile number
         */
        ::uint16_t tile;
    };

    /** Base class for InterOp records that contain tile specific metrics per cycle
     *
     * These records contain both a lane, tile and cycle identifier.
     *
     * @note These classes are packed such that there is not padding. Their size reflects the accumulation of their
     * member fields.
     */
    struct base_cycle_metric : base_metric
    {
        /** Constructor
         *
         * @param lane_ lane number
         * @param tile_ tile number
         * @param cycle_ cycle number
         */
        base_cycle_metric(::uint16_t lane_ = 0, ::uint16_t tile_ = 0, ::uint16_t cycle_ = 0) :
                base_metric(lane_, tile_), cycle(cycle_)
        {
        }

        /** Set the lane, tile and cycle id from a base metric
         *
         * @param metric a base_metric from the model
         */
        template<class BaseMetric>
        void set(const BaseMetric &metric)
        {
            base_metric::set(metric);
            cycle = static_cast< ::uint16_t >(metric.cycle());
        }

        /** Test if the layout contains valid data
         *
         * @return true if data is valid
         */
        bool is_valid(const bool check_tile) const
        {
            return base_metric::is_valid(check_tile) && cycle > 0;
        }

        /** Cycle number
         */
        ::uint16_t cycle;
    };

    /** Base class for InterOp records that contain tile specific metrics per read
     *
     * These records contain both a lane, tile and read identifier.
     *
     * @note These classes are packed such that there is not padding. Their size reflects the accumulation
     * of their member fields.
     */
    struct base_read_metric : base_metric
    {
        /** Constructor
         *
         * @param lane_ lane number
         * @param tile_ tile number
         * @param read_ read number
         */
        base_read_metric(::uint16_t lane_ = 0, ::uint16_t tile_ = 0, ::uint16_t read_ = 0) :
                base_metric(lane_, tile_), read(read_)
        {
        }

        /** Set the lane, tile and read id from a base metric
         *
         * @param metric a base_metric from the model
         */
        template<class BaseMetric>
        void set(const BaseMetric &metric)
        {
            base_metric::set(metric);
            read = static_cast< ::uint16_t >(metric.read());
        }

        /** Test if the layout contains valid data
         *
         * @return true if data is valid
         */
        bool is_valid(const bool check_tile) const
        {
            return base_metric::is_valid(check_tile) && read > 0;
        }

        /** Read number
         */
        ::uint16_t read;
    };

#pragma pack()
}}}}


